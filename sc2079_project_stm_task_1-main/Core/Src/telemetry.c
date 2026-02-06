///*
// * telemetry.c
// *
// *  Created on: Sep 30, 2025
// *      Author: rachm
// */
//
//
//extern UART_HandleTypeDef huart3;
//
//void Telemetry_Init(void) {
//  gTelemQ = osMessageQueueNew(64, sizeof(Telemetry), NULL); // depth 64
//}
//static inline void Telemetry_Push(float vL,float vR,float remL,float remR,
//                                  float vRefL,float vRefR,int pwmL,int pwmR,float dt)
//{
//  Telemetry t = { vL, vR, remL, remR, vRefL, vRefR, pwmL, pwmR, dt };
//  (void)osMessageQueuePut(gTelemQ, &t, 0, 0); // non-blocking; drops if full
//}
//
//{
//        static uint32_t last_tx_ms = 0;
//        uint32_t t_ms = HAL_GetTick();
//        if (t_ms - last_tx_ms >= 20U) { // ~50 Hz
//          char line[160];
//          int n = snprintf(line, sizeof(line),
//              "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\r\n",
//			  (t.remL/1560.0f)*6.5f,
//				(t.remR/1560.0f)*6.5f,
//				vL,
//				vR,
//				vRefL,
//				vRefR,
//				pwmVal_L,
//				pwmVal_R,
//				error_angle,
//				target_angle,
//				total_angle
//			);              // right PWM
//
//          if (n > 0) {
//            // Uses huart3 declared in main.h (extern)
//            HAL_UART_Transmit(&huart3, (uint8_t*)line, (uint16_t)n, 2);
//          }
//          last_tx_ms = t_ms;
//        }
//      }
