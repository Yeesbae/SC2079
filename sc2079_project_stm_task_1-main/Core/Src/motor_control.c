#include "motor_control.h"

//#define DUTY_MAX   550         // 799
#define DUTY_HI    550   // ~759
#define DUTY_MD    550   // ~559
#define DUTY_LO    550   // ~359
//#define DUTY_MIN   550   // ~199
#define DUTY_CREEP 550   // ~95 (tiny nudge)

extern int times_acceptable;
extern double total_angle;
extern double target_angle;
extern double error_angle;
extern UART_HandleTypeDef huart3;
extern int straight_correction;

static int32_t prevEncL = 0, prevEncR = 0;

// PID controller instances
PID pidL = { .kp = 0.2f, .ki = 0.05f, .kd = 0.02f, .i = 0, .prev_err = 0 };
PID pidR = { .kp = 0.2f, .ki = 0.05f, .kd = 0.02f, .i = 0, .prev_err = 0 };

//PID pidL = { .kp = 0.05f, .ki = 0.002f, .kd = 0.001f, .i = 0, .prev_err = 0 };
//PID pidR = { .kp = 0.05f, .ki = 0.002f, .kd = 0.001f, .i = 0, .prev_err = 0 };

// Position and sync gains
const float Kpos  = 2.5f;
const float Ksync = 2.5f;
static const float ANG_ERR_MAX       = 30.0f;  // degrees
static const float TURN_FACTOR_GAIN  = 0.6f;   // how much to slow inner wheel
static const float TURN_FACTOR_MIN   = 0.4f;   // clamp for inner wheel speed

static inline float sgnf(float x){ return (x > 0) - (x < 0); }

// Velocity PID function (signed output)
int vel_pid(PID* pid, float target_v, float meas_v, float dt)
{
    float e = target_v - meas_v;

    // --- Derivative ---
    float d = (dt > 0) ? pid->kd * (e - pid->prev_err) / dt : 0.0f;

    // --- Conditional integrator (simple anti-windup) ---
    // We'll compute provisional output, and if saturated & still pushing outward, don't integrate.
    float p = pid->kp * e;
    float i_next = pid->i + pid->ki * e * dt;

    // Base “kick” to overcome motor deadband in the *commanded direction*
    const float base = sgnf(target_v) * CTRL_PWM_CLAMP;

    // Provisional output using i_next
    float u = base + p + i_next + d;

    // Anti-windup: only accept i_next if not pushing against saturation
    // If saturated and the integrator would push further outward, freeze i.
    bool sat_pos = (u >=  PWM_MAX - 1e-6f);
    bool sat_neg = (u <= -PWM_MAX + 1e-6f);
    bool pushing_outward = (sat_pos && (i_next > pid->i)) || (sat_neg && (i_next < pid->i));
    if (!pushing_outward) {
        pid->i = i_next;
    }

    pid->prev_err = e;
//    temp1 = u;
    return (int)u;  // signed PWM
}

void motor_update_straight(int32_t leftTarget, int32_t rightTarget,
                           int32_t leftEncoderVal, int32_t rightEncoderVal, float dt)
{
    // --- Encoder deltas ---
    int32_t dEncL = leftEncoderVal  - prevEncL;
    int32_t dEncR = rightEncoderVal - prevEncR;
    prevEncL = leftEncoderVal;
    prevEncR = rightEncoderVal;

    // --- Measured wheel speeds (ticks/sec) ---
    float vL = dEncL / dt;
    float vR = dEncR / dt;

    // --- Remaining distance (ticks) ---
    float remL = (float)(leftTarget  - leftEncoderVal);
    float remR = (float)(rightTarget - rightEncoderVal);

    float pos_err = fmaxf(fabsf(remL), fabsf(remR));
    if (pos_err <= STRAIGHT_POS_TOL) times_acceptable++;

    // --- Outer loop: position -> target velocity ---
    float vRefL = CLAMP(Kpos * remL, -CTRL_VMAX_TICKS, CTRL_VMAX_TICKS);
    float vRefR = CLAMP(Kpos * remR, -CTRL_VMAX_TICKS, CTRL_VMAX_TICKS);

    // --- Straight-line sync correction ---
    float diffRem = remL - remR;
    vRefL += Ksync * diffRem;
    vRefR -= Ksync * diffRem;

    if (straight_correction) {
		// Proportional slowdown: 0°→no reduction, 5°+→15% max reduction
		float heading_scale = 1.0f - 0.15f * fminf(fabsf((float)error_angle) / 5.0f, 1.0f);
		vRefL *= heading_scale;
		vRefR *= heading_scale;
	}
//    else if (vRefL < 0 && vRefL < 0) {
//		vRefL *= 0.5;
//		vRefR *= 0.5;
//	}

    // --- Inner loop: velocity PID -> PWM ---
    int pwmVal_L = vel_pid(&pidL, vRefL, vL, dt);
    int pwmVal_R = vel_pid(&pidR, vRefR, vR, dt);

    // Apply PWM to your hardware
    motor_set_pwm_left(pwmVal_L);
    motor_set_pwm_right(pwmVal_R);
//
//    {
//        static uint32_t last_tx_ms = 0;
//        uint32_t t_ms = HAL_GetTick();
//        if (t_ms - last_tx_ms >= 20U) { // ~50 Hz
//            // Make sure these types are correct:
//            // remL, remR, vL, vR, vRefL, vRefR, error_angle, target_angle, total_angle -> float
//            // pwmVal_L, pwmVal_R -> int
//            char line[200];
//            int n = snprintf(line, sizeof(line),
//                "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d,%.2f,%.2f,%.2f\r\n",
//                (remL/1560.0f)*6.5f*M_PI,
//                (remR/1560.0f)*6.5f*M_PI,
//                vL,
//                vR,
//                vRefL,
//                vRefR,
//                pwmVal_L,
//                pwmVal_R,
//                error_angle,
//                target_angle,
//                total_angle
//            );
//            if (n > 0 && n < (int)sizeof(line)) {
//                // Give enough time to transmit the longer line
//                HAL_UART_Transmit(&huart3, (uint8_t*)line, (uint16_t)n, 20);
//            }
//            last_tx_ms = t_ms;
//        }
//    }
}

// --- Cruise mode state (module-level so motor_cruise_reset can access) ---
static int32_t cruise_base_L = 0, cruise_base_R = 0;
static int cruise_active = 0;

void motor_update_cruise(int32_t leftEncoderVal, int32_t rightEncoderVal, float dt)
{
    // Same as motor_update_straight but with constant target velocity
    // instead of position-derived velocity. Uses the same velocity PID
    // so each wheel adapts its PWM to match the target speed.

    // --- Encoder deltas ---
    int32_t dEncL = leftEncoderVal  - prevEncL;
    int32_t dEncR = rightEncoderVal - prevEncR;
    prevEncL = leftEncoderVal;
    prevEncR = rightEncoderVal;

    // --- Measured wheel speeds (ticks/sec) ---
    float vL = dEncL / dt;
    float vR = dEncR / dt;

    // --- Constant target velocity (CRUISE_PWM mapped to ticks/sec) ---
    float vRef = (float)CRUISE_PWM * ((float)CTRL_VMAX_TICKS / (float)PWM_MAX);
    float vRefL = vRef;
    float vRefR = vRef;

    // --- Sync correction: keep both wheels at same travel distance ---
    if (!cruise_active) {
        cruise_base_L = leftEncoderVal;
        cruise_base_R = rightEncoderVal;
        // Reset prevEnc so first delta is zero (no velocity spike)
        prevEncL = leftEncoderVal;
        prevEncR = rightEncoderVal;
        cruise_active = 1;
    }
    float drift = (float)(leftEncoderVal - cruise_base_L)
                - (float)(rightEncoderVal - cruise_base_R);
    vRefL -= Ksync * drift;
    vRefR += Ksync * drift;

    // --- Heading correction (same as motor_update_straight) ---
    if (straight_correction) {
        float heading_scale = 1.0f - 0.15f * fminf(fabsf((float)error_angle) / 5.0f, 1.0f);
        vRefL *= heading_scale;
        vRefR *= heading_scale;
    }

    // --- Inner loop: velocity PID -> PWM ---
    int pwmVal_L = vel_pid(&pidL, vRefL, vL, dt);
    int pwmVal_R = vel_pid(&pidR, vRefR, vR, dt);

    motor_set_pwm_left(pwmVal_L);
    motor_set_pwm_right(pwmVal_R);
}

void motor_cruise_reset(void)
{
    cruise_active = 0;
    // Reset PID state so cruise starts clean
    pidL.i = 0; pidL.prev_err = 0;
    pidR.i = 0; pidR.prev_err = 0;
}

static inline float turn_factor_from_duty(int duty){
    float duty_ratio = (float)(duty - DUTY_MIN) / (float)(DUTY_MAX - DUTY_MIN); // 0..1
    float tf = 1.0f - TURN_FACTOR_GAIN * duty_ratio;
    return CLAMP(tf, TURN_FACTOR_MIN, 1.0f);
}

int PID_Angle(double errord) {
	float a = fabsf((float)errord);

	if (a < 1.0f) {
		times_acceptable++;
		return 0;
	}

	// Constant speed for consistent radius, higher than original
	if (a > 10.0f) return 600;    // Flat throughout turn
	return 500;                    // Final 1-10°: gentle approach
}

//int PID_Angle(float error_angle_deg)
//{
//    // 1. take absolute error
//    float a = fabsf(error_angle_deg);
//
//    if (a <= TURN_ANGLE_TOL_DEG) {
//		times_acceptable++;
//	}
//
//    // 2. choose at what angle you want to hit DUTY_MAX
//    const float ANG_FULLSCALE_DEG = 90.0f; // tune: 30° → max speed
//
//    // 3. fraction 0..1
//    float frac = a / ANG_FULLSCALE_DEG;
//    if (frac > 1.0f) frac = 1.0f;
//
//    // 4. linear interpolation
//    float pwm = (float)DUTY_MIN + frac * (float)(DUTY_MAX - DUTY_MIN);
//
//    return (int)(pwm + 0.5f);
//}

void motor_update_turn(double error_angle, float dt, int dir){
    (void)dt;
    int duty = PID_Angle(error_angle);
//    float turnFactor = turn_factor_from_duty(duty);
    float turnFactor = 0.59;

    if (error_angle > 0){
        motor_set_pwm_right(duty);
        motor_set_pwm_left((int)(duty * turnFactor));
    } else {
        motor_set_pwm_left(duty);
        motor_set_pwm_right((int)(duty * turnFactor));
    }
}

void motor_set_pwm_right(int16_t cmd){
  int16_t mag = cmd<0 ? -cmd : cmd;
  mag = CLAMP(mag,PWM_MIN,PWM_MAX);

  if (cmd > 0){
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_2, mag); // left wheel forward
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_1, 0); // left wheel backward
  } else if (cmd < 0) {
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_1, mag); // left wheel backward
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_2, 0); // left wheel forward
  } else {
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_1, PWM_MAX); // stop
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_2, PWM_MAX); // stop
  }
}

void motor_set_pwm_left(int16_t cmd){
  int16_t mag = cmd<0 ? -cmd : cmd;
  mag = CLAMP(mag,PWM_MIN,PWM_MAX);

  if (cmd > 0){
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_4, mag); // right wheel forward
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_3, 0); // right wheel backward
  } else if (cmd < 0) {
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_3, mag); // right wheel backward
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_4, 0); // right wheel forward
  } else {
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_3, PWM_MAX); // stop
   __HAL_TIM_SetCompare(&htim1, TIM_CHANNEL_4, PWM_MAX); // stop
  }
}
