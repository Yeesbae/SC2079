#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include "stm32f4xx_hal.h"
#include <stdbool.h>
#include "cmsis_os2.h"
#include <math.h>

extern TIM_HandleTypeDef htim1;

#define CLAMP(x, lo, hi)  ((x) < (lo) ? (lo) : ((x) > (hi) ? (hi) : (x)))

// --- Constants ---
#define CTRL_PWM_MIN      0
#define CTRL_PWM_CLAMP    450    // just-overcome-friction duty
#define CTRL_VMAX_TICKS   18000   // max ticks/s allowed (speed limit)
#define CTRL_A_RAMP       4000   // ticks/s^2 (accel limit for smoothness)

// TODO TIM1 PSC=0, ARR=799 (16 MHz / 800 => 20 kHz)
#define PWM_RATIO 0.991

#define PWM_MAX    799   // 799
#define PWM_MIN    450   // ~199
#define DUTY_MAX    700   // 799
#define DUTY_MIN    550   // ~199
#define CRUISE_PWM  650  // slow speed for testing (just above 450 deadband)

#define TURN_ANGLE_TOL_DEG 0.5f
#define STRAIGHT_POS_TOL 100


// --- PID structure ---
typedef struct {
    float kp, ki, kd;
    float i;         // integrator
    float prev_err;  // last error
} PID;

// --- Functions ---
int vel_pid(PID* pid, float target, float meas, float dt);
void motor_update_turn(double error_angle, float dt, int dir);
void motor_update_straight(int32_t leftTarget, int32_t rightTarget,
                           int32_t leftEncoderVal, int32_t rightEncoderVal, float dt);
void motor_update_cruise(int32_t leftEncoderVal, int32_t rightEncoderVal, float dt);
void motor_cruise_reset(void);
void motor_set_pwm_left(int16_t cmd);
void motor_set_pwm_right(int16_t cmd);

#endif // MOTOR_CONTROL_H
