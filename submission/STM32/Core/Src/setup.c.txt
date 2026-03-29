#include "setup.h"

int Is_First_Captured = 0;
int32_t IC_Val1 = 0;
int32_t IC_Val2 = 0;
uint32_t Difference = 0;
int k=0;
volatile uint16_t uDistance = 0;

static void Ultrasonic_ResetCapture(void) {
  // Stop capture + its IRQ to start from a clean state
 __HAL_TIM_DISABLE_IT(&htim12, TIM_IT_CC2);
   HAL_TIM_IC_Stop_IT(&htim12, TIM_CHANNEL_2);

   Is_First_Captured = 0;
   IC_Val1 = 0;
   IC_Val2 = 0;
   uDistance = 0;

   __HAL_TIM_SET_COUNTER(&htim12, 0);
   __HAL_TIM_SET_CAPTUREPOLARITY(&htim12, TIM_CHANNEL_2, TIM_INPUTCHANNELPOLARITY_RISING);

   HAL_TIM_IC_Start_IT(&htim12, TIM_CHANNEL_2);
}

static void delay_until_ms(uint32_t *last_ms, uint32_t period_ms) {
  uint32_t next = *last_ms + period_ms;
  uint32_t now  = HAL_GetTick();
  if ((int32_t)(next - now) > 0) {
    HAL_Delay(next - now);
  }
  *last_ms = next;
}

int Ultrasonic_ResetUntilStable(uint16_t *stable_cm_out, uint32_t timeout_ms) {
 uint32_t t0 = HAL_GetTick();

   while ((HAL_GetTick() - t0) < timeout_ms) {

     // 1) Hard reset the capture state
     Ultrasonic_ResetCapture();

     // 2) Flush a few measurements
     uint32_t last = HAL_GetTick();
     for (uint32_t i = 0; i < US_FLUSH_MEAS; ++i) {
       HCSR04_Read();                    // trigger one ping
       delay_until_ms(&last, US_PERIOD_MS);
       (void)uDistance;                  // let ISR update it
       if ((HAL_GetTick() - t0) >= timeout_ms) return 0;
     }

     // 3) Collect a window
     uint16_t buf[US_SAMPLES];
     last = HAL_GetTick();
     for (uint32_t i = 0; i < US_SAMPLES; ++i) {
       HCSR04_Read();
       delay_until_ms(&last, US_PERIOD_MS);
       buf[i] = uDistance;               // updated in TIM12 CH2 ISR
       if ((HAL_GetTick() - t0) >= timeout_ms) break;
     }

     // 4) Check consistency
     uint16_t minv = 0xFFFF, maxv = 0;
     uint32_t sum = 0, good = 0;
     for (uint32_t i = 0; i < US_SAMPLES; ++i) {
       uint16_t d = buf[i];
       if (d >= US_MIN_VALID_CM) {
         if (d < minv) minv = d;
         if (d > maxv) maxv = d;
         sum += d; good++;
       }
     }

     if (good >= (US_SAMPLES - 2)) {             // allow up to 2 outliers
       if ((maxv - minv) <= US_SPREAD_MAX_CM) {
         if (stable_cm_out) *stable_cm_out = (uint16_t)(sum / good);
         return 1;                                // stable!
       }
     }

     // 5) Not stable yet → small pause and try again
     HAL_Delay(50);
   }

   return 0;  // timed out
}


