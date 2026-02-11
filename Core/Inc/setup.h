#ifndef SETUP_H
#define SETUP_H

#include "stm32f4xx_hal.h"
#include "ICM20948.h"

// GYRO
#define GYRO_SAMPLE_MS        10u     // 100 Hz during calibration

// ULTRASONIC
#define US_SAMPLES            10U   // samples per window
#define US_FLUSH_MEAS         3U    // warm-up triggers after reset
#define US_SPREAD_MAX_CM      2U    // max (max - min) allowed in a window
#define US_MIN_VALID_CM       3U    // ignore 0/too-near echoes
#define US_PERIOD_MS          20U

/* Ultrasonic (HC-SR04) */
extern int Is_First_Captured;
extern int32_t IC_Val1;
extern int32_t IC_Val2;
extern uint32_t Difference;
extern volatile uint16_t uDistance;
extern int k;
extern TIM_HandleTypeDef htim12;

// Ultrasonic
int Ultrasonic_ResetUntilStable(uint16_t *stable_cm_out, uint32_t timeout_ms);

#endif // SETUP_H
