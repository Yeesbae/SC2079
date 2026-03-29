/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define ENCODER_D_Pin GPIO_PIN_0
#define ENCODER_D_GPIO_Port GPIOA
#define ENCODER_DA1_Pin GPIO_PIN_1
#define ENCODER_DA1_GPIO_Port GPIOA
#define LED3_Pin GPIO_PIN_8
#define LED3_GPIO_Port GPIOE
#define CIN2_Pin GPIO_PIN_9
#define CIN2_GPIO_Port GPIOE
#define CIN1_Pin GPIO_PIN_11
#define CIN1_GPIO_Port GPIOE
#define DIN2_Pin GPIO_PIN_13
#define DIN2_GPIO_Port GPIOE
#define DIN1_Pin GPIO_PIN_14
#define DIN1_GPIO_Port GPIOE
#define ECHO_Pin GPIO_PIN_15
#define ECHO_GPIO_Port GPIOB
#define OLED_DC_Pin GPIO_PIN_11
#define OLED_DC_GPIO_Port GPIOD
#define OLED_RES_Pin GPIO_PIN_12
#define OLED_RES_GPIO_Port GPIOD
#define OLED_SDA_Pin GPIO_PIN_13
#define OLED_SDA_GPIO_Port GPIOD
#define OLED_SCL_Pin GPIO_PIN_14
#define OLED_SCL_GPIO_Port GPIOD
#define SERVO_Pin GPIO_PIN_6
#define SERVO_GPIO_Port GPIOC
#define TRIGGER_Pin GPIO_PIN_7
#define TRIGGER_GPIO_Port GPIOC
#define ENCODER_C_Pin GPIO_PIN_6
#define ENCODER_C_GPIO_Port GPIOB
#define ENCODER_CB7_Pin GPIO_PIN_7
#define ENCODER_CB7_GPIO_Port GPIOB
#define USER_PB_Pin GPIO_PIN_0
#define USER_PB_GPIO_Port GPIOE

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
