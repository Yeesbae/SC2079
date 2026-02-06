/* USER CODE BEGIN Header */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "cmsis_os.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "oled.h"
#include "setup.h"
#include "motor_control.h"
#include <stdio.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* ------------------------ Tunables / quick macros ------------------------- */
// TODO REMOVE
/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */


#define TEST 1

#define ENCODER_TPR          1560
#define WHEEL_DIAMETER_CM    6.5f   // Diameter of wheel in mm
#define WHEEL_BASE_CM        15.0f  // Distance between wheels in mm
#define WHEEL_CIRC_CM        (M_PI * WHEEL_DIAMETER_CM)  // Wheel circumference in mm
#define TICK_TO_CM           (ENCODER_TPR / WHEEL_CIRC_CM)  // Conversion from encoder ticks to mm

#define TURN_TIMEOUT_MS 1000

#define CLAMP(x,lo,hi) ((x)<(lo)?(lo):((x)>(hi)?(hi):(x)))

// TODO TIM3 PSC=319, ARR=1000 (16 MHz / (319+1) = 50 kHz => 1000 ticks = 20 ms).
#define SERVO_TICKS_FROM_MS(ms) ((uint16_t)((ms) * 50.0)) // 1 tick = 20us
//#define SERVOCENTER 76 // SERVO_TICKS_FROM_MS(1.50)  // 75
//#define SERVORIGHT  106 // SERVO_TICKS_FROM_MS(2.00)  // 100
//#define SERVOLEFT   46 // SERVO_TICKS_FROM_MS(1.00)  // 50
//#define LEFT_LIMIT  56
//#define RIGHT_LIMIT 96

#define SERVOCENTER 77 // SERVO_TICKS_FROM_MS(1.50)  // 75
#define SERVORIGHT  130 // SERVO_TICKS_FROM_MS(2.00)  // 100
#define SERVOLEFT   45 // SERVO_TICKS_FROM_MS(1.00)  // 50
#define LEFT_LIMIT  SERVOLEFT + 10
#define RIGHT_LIMIT SERVORIGHT - 10
#define SERVO_ERR_TO_CCR_GAIN  14.0/5.0

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
I2C_HandleTypeDef hi2c2;

TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
TIM_HandleTypeDef htim4;
TIM_HandleTypeDef htim12;

UART_HandleTypeDef huart3;

/* Definitions for defaultTask */
osThreadId_t defaultTaskHandle;
const osThreadAttr_t defaultTask_attributes = {
  .name = "defaultTask",
  .stack_size = 128 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* Definitions for communicateTask */
osThreadId_t communicateTaskHandle;
const osThreadAttr_t communicateTask_attributes = {
  .name = "communicateTask",
  .stack_size = 512 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* Definitions for motorTask */
osThreadId_t motorTaskHandle;
const osThreadAttr_t motorTask_attributes = {
  .name = "motorTask",
  .stack_size = 512 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* Definitions for encoderTask */
osThreadId_t encoderTaskHandle;
const osThreadAttr_t encoderTask_attributes = {
  .name = "encoderTask",
  .stack_size = 512 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* Definitions for gyroTask */
osThreadId_t gyroTaskHandle;
const osThreadAttr_t gyroTask_attributes = {
  .name = "gyroTask",
  .stack_size = 512 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* Definitions for OLEDTask */
osThreadId_t OLEDTaskHandle;
const osThreadAttr_t OLEDTask_attributes = {
  .name = "OLEDTask",
  .stack_size = 256 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* Definitions for ultrasonicTask */
osThreadId_t ultrasonicTaskHandle;
const osThreadAttr_t ultrasonicTask_attributes = {
  .name = "ultrasonicTask",
  .stack_size = 512 * 4,
  .priority = (osPriority_t) osPriorityLow,
};
/* USER CODE BEGIN PV */

/* UART rx */
float temp1 = 0;
float temp2 = 0;
float temp3 = 0;
int temp4 = 0;
int temp5 = 0;

uint8_t aRxBuffer[5] = {0};
int flagDone = 0;
int magnitude = 0;

/* Motion state */
volatile int pwmVal_L = 0, pwmVal_R = 0, pwmVal_servo = SERVOCENTER;
volatile int times_acceptable = 0;
int e_brake = 1;          // emergency brake flag
int straight_correction = 1;

volatile int32_t leftEncoderVal  = 0,  rightEncoderVal = 0;
volatile int32_t leftTarget      = 0,  rightTarget     = 0;

/* Heading */
double total_angle = 0.0;
double target_angle = 0.0;
double error_angle  = 0.0;

/* Gyro (ICM) */
IMU_Data imu;
float bias_z_dps;
int gyro_ready = 0;
//const float DEADBAND_DPS = 0.25f;

/* Task loop counters - to verify tasks are running */
volatile uint32_t cnt_communicate = 0;
volatile uint32_t cnt_motor = 0;
volatile uint32_t cnt_encoder = 0;
volatile uint32_t cnt_gyro = 0;
volatile uint32_t cnt_oled = 0;
volatile uint32_t cnt_ultrasonic = 0;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART3_UART_Init(void);
static void MX_TIM1_Init(void);
static void MX_I2C2_Init(void);
static void MX_TIM4_Init(void);
static void MX_TIM2_Init(void);
static void MX_TIM3_Init(void);
static void MX_TIM12_Init(void);
void StartDefaultTask(void *argument);
void startCommunicateTask(void *argument);
void startMotorTask(void *argument);
void startEncoderTask(void *argument);
void startGyroTask(void *argument);
void startOLEDTask(void *argument);
void startUltrasonicTask(void *argument);

/* USER CODE BEGIN PFP */

/* Movement API */
void moveCarStraight(double distance);
void moveCarStop(void);
void moveCarRight(double angle);
void moveCarLeft(double angle);

/* PID (kept from your reference) */
int finishCheck(void);

/* Ultrasonic helpers */
void delay(uint16_t time);
void HCSR04_Read(void);

void TestOLED(const char *msg);  // stub here if OLED lib not linked
static void fatal_blink_and_park(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
void TestOLED(const char *msg) {
	OLED_Clear();                        // optional, if you want a clean screen
	OLED_ShowString(0, 0, (uint8_t*)msg);
	OLED_Refresh_Gram();
}

static void fatal_blink_and_park(void){
    for (int i=0;i<100;i++){
        HAL_GPIO_WritePin(LED3_GPIO_Port, LED3_Pin, GPIO_PIN_SET);
        HAL_Delay(100);
        HAL_GPIO_WritePin(LED3_GPIO_Port, LED3_Pin, GPIO_PIN_RESET);
        HAL_Delay(100);
    }
    // Park forever (low power)
    for(;;){ __WFI(); }
}
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */
  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */
  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */
  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART3_UART_Init();
  MX_TIM1_Init();
  MX_I2C2_Init();
  MX_TIM4_Init();
  MX_TIM2_Init();
  MX_TIM3_Init();
  MX_TIM12_Init();
  /* USER CODE BEGIN 2 */

  OLED_Init();

  /* Start PWM outputs */
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1); // PE9  CIN2
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2); // PE11 CIN1
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_3); // PE13 DIN2
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_4); // PE14 DIN1
  __HAL_TIM_MOE_ENABLE(&htim1);

  HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1); // PC6 SERVO
  pwmVal_servo = SERVOCENTER;  // keep this so the first pulse is centered
  __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1,
    CLAMP(pwmVal_servo, 0, __HAL_TIM_GET_AUTORELOAD(&htim3)));

  /* UART RX IT */
  HAL_UART_Receive_IT(&huart3, aRxBuffer, 5);

  /* ========== UART TEST START ========== */
  // Test message to transmit via UART3
  uint8_t testMsg[] = "STM32 UART3 Ready!";

  // Transmit test message (will appear on PC/RPi terminal)
  HAL_UART_Transmit(&huart3, testMsg, sizeof(testMsg) - 1, 100);
  HAL_UART_Transmit(&huart3, (uint8_t*)"\r\n", 2, 100);

  // Display confirmation on OLED
  OLED_Clear();
  OLED_ShowString(0, 0, testMsg);  // Show testMsg at top of screen
  OLED_ShowString(0, 16, (uint8_t*)"TX: 115200 8N1");
  OLED_ShowString(0, 32, (uint8_t*)"Msg Sent!");
  OLED_ShowString(0, 48, (uint8_t*)"Check Terminal");
  OLED_Refresh_Gram();

  // Brief delay so user can see the message
  HAL_Delay(2000);

  OLED_Clear();
  OLED_ShowString(0, 0, (uint8_t*)"Waiting for cmd");
  OLED_ShowString(0, 16, (uint8_t*)"Format: XYNNN");
  OLED_ShowString(0, 32, (uint8_t*)"X=S/R/L/U");
  OLED_ShowString(0, 48, (uint8_t*)"Y=F/B NNN=val");
  OLED_Refresh_Gram();

  HAL_Delay(1000);
  /* ========== UART TEST END ========== */

//  uint8_t status = ICM20948_init(&imu, &hi2c2);
//
//	float gyro_bias_z = 0.0f;
//	if (!Gyro_CalibrateAndWaitStable(&imu, &hi2c2, 8000u, &gyro_bias_z)) {
//	  // Calibration failed → handle error (blink LED, halt, retry loop, etc.)
//	  Error_Handler();
//	}
//
//	// Store into global variable for tasks
//	bias_z_dps = gyro_bias_z;

	uint16_t us_zero = 0;
	Ultrasonic_ResetUntilStable(&us_zero, 3000U);

  /* USER CODE END 2 */

  /* Init scheduler */
  osKernelInitialize();

  /* USER CODE BEGIN RTOS_MUTEX */
  /* USER CODE END RTOS_MUTEX */

  /* USER CODE BEGIN RTOS_SEMAPHORES */
  /* USER CODE END RTOS_SEMAPHORES */

  /* USER CODE BEGIN RTOS_TIMERS */
  /* USER CODE END RTOS_TIMERS */

  /* USER CODE BEGIN RTOS_QUEUES */
  /* USER CODE END RTOS_QUEUES */

  /* Create the thread(s) */
  /* creation of defaultTask */
  //defaultTaskHandle = osThreadNew(StartDefaultTask, NULL, &defaultTask_attributes);

  /* creation of communicateTask */
  communicateTaskHandle = osThreadNew(startCommunicateTask, NULL, &communicateTask_attributes);

  /* creation of motorTask */
  motorTaskHandle = osThreadNew(startMotorTask, NULL, &motorTask_attributes);

  /* creation of encoderTask */
  encoderTaskHandle = osThreadNew(startEncoderTask, NULL, &encoderTask_attributes);

  /* creation of gyroTask */
  gyroTaskHandle = osThreadNew(startGyroTask, NULL, &gyroTask_attributes);

  /* creation of OLEDTask */
  OLEDTaskHandle = osThreadNew(startOLEDTask, NULL, &OLEDTask_attributes);

  /* creation of ultrasonicTask */
  ultrasonicTaskHandle = osThreadNew(startUltrasonicTask, NULL, &ultrasonicTask_attributes);

  /* USER CODE BEGIN RTOS_THREADS */
  /* USER CODE END RTOS_THREADS */

  /* USER CODE BEGIN RTOS_EVENTS */
  /* USER CODE END RTOS_EVENTS */

  /* Start scheduler */
  osKernelStart();

  /* We should never get here as control is now taken by the scheduler */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C2_Init(void)
{

  /* USER CODE BEGIN I2C2_Init 0 */

  /* USER CODE END I2C2_Init 0 */

  /* USER CODE BEGIN I2C2_Init 1 */

  /* USER CODE END I2C2_Init 1 */
  hi2c2.Instance = I2C2;
  hi2c2.Init.ClockSpeed = 100000;
  hi2c2.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c2.Init.OwnAddress1 = 0;
  hi2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c2.Init.OwnAddress2 = 0;
  hi2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C2_Init 2 */

  /* USER CODE END I2C2_Init 2 */

}

/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(void)
{

  /* USER CODE BEGIN TIM1_Init 0 */

  /* USER CODE END TIM1_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 0;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = 799;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_2) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_3) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_4) != HAL_OK)
  {
    Error_Handler();
  }
  sBreakDeadTimeConfig.OffStateRunMode = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime = 0;
  sBreakDeadTimeConfig.BreakState = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */
  HAL_TIM_MspPostInit(&htim1);

}

/**
  * @brief TIM2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM2_Init(void)
{

  /* USER CODE BEGIN TIM2_Init 0 */

  /* USER CODE END TIM2_Init 0 */

  TIM_Encoder_InitTypeDef sConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM2_Init 1 */

  /* USER CODE END TIM2_Init 1 */
  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 0;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = 4294967295;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  sConfig.EncoderMode = TIM_ENCODERMODE_TI12;
  sConfig.IC1Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC1Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC1Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC1Filter = 10;
  sConfig.IC2Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC2Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC2Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC2Filter = 10;
  if (HAL_TIM_Encoder_Init(&htim2, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM2_Init 2 */

  /* USER CODE END TIM2_Init 2 */

}

/**
  * @brief TIM3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM3_Init(void)
{

  /* USER CODE BEGIN TIM3_Init 0 */

  /* USER CODE END TIM3_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};

  /* USER CODE BEGIN TIM3_Init 1 */

  /* USER CODE END TIM3_Init 1 */
  htim3.Instance = TIM3;
  htim3.Init.Prescaler = 319;
  htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim3.Init.Period = 1000;
  htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim3) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim3, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_Init(&htim3) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM3_Init 2 */

  /* USER CODE END TIM3_Init 2 */
  HAL_TIM_MspPostInit(&htim3);

}

/**
  * @brief TIM4 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM4_Init(void)
{

  /* USER CODE BEGIN TIM4_Init 0 */

  /* USER CODE END TIM4_Init 0 */

  TIM_Encoder_InitTypeDef sConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM4_Init 1 */

  /* USER CODE END TIM4_Init 1 */
  htim4.Instance = TIM4;
  htim4.Init.Prescaler = 0;
  htim4.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim4.Init.Period = 65535;
  htim4.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim4.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  sConfig.EncoderMode = TIM_ENCODERMODE_TI12;
  sConfig.IC1Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC1Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC1Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC1Filter = 10;
  sConfig.IC2Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC2Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC2Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC2Filter = 10;
  if (HAL_TIM_Encoder_Init(&htim4, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim4, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM4_Init 2 */

  /* USER CODE END TIM4_Init 2 */

}

/**
  * @brief TIM12 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM12_Init(void)
{

  /* USER CODE BEGIN TIM12_Init 0 */

  /* USER CODE END TIM12_Init 0 */

  TIM_IC_InitTypeDef sConfigIC = {0};

  /* USER CODE BEGIN TIM12_Init 1 */

  /* USER CODE END TIM12_Init 1 */
  htim12.Instance = TIM12;
  htim12.Init.Prescaler = 15;
  htim12.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim12.Init.Period = 65535;
  htim12.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim12.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_IC_Init(&htim12) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigIC.ICPolarity = TIM_INPUTCHANNELPOLARITY_RISING;
  sConfigIC.ICSelection = TIM_ICSELECTION_DIRECTTI;
  sConfigIC.ICPrescaler = TIM_ICPSC_DIV1;
  sConfigIC.ICFilter = 0;
  if (HAL_TIM_IC_ConfigChannel(&htim12, &sConfigIC, TIM_CHANNEL_2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM12_Init 2 */

  /* USER CODE END TIM12_Init 2 */

}

/**
  * @brief USART3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART3_UART_Init(void)
{

  /* USER CODE BEGIN USART3_Init 0 */
  /* USER CODE END USART3_Init 0 */

  /* USER CODE BEGIN USART3_Init 1 */
  /* USER CODE END USART3_Init 1 */
  huart3.Instance = USART3;
  huart3.Init.BaudRate = 115200;
  huart3.Init.WordLength = UART_WORDLENGTH_8B;
  huart3.Init.StopBits = UART_STOPBITS_1;
  huart3.Init.Parity = UART_PARITY_NONE;
  huart3.Init.Mode = UART_MODE_TX_RX;
  huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart3.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART3_Init 2 */
  /* USER CODE END USART3_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */
  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LED3_GPIO_Port, LED3_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOD, OLED_DC_Pin|OLED_RES_Pin|OLED_SDA_Pin|OLED_SCL_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(TRIGGER_GPIO_Port, TRIGGER_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : LED3_Pin */
  GPIO_InitStruct.Pin = LED3_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LED3_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pins : OLED_DC_Pin OLED_RES_Pin OLED_SDA_Pin OLED_SCL_Pin */
  GPIO_InitStruct.Pin = OLED_DC_Pin|OLED_RES_Pin|OLED_SDA_Pin|OLED_SCL_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

  /*Configure GPIO pin : TRIGGER_Pin */
  GPIO_InitStruct.Pin = TRIGGER_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(TRIGGER_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : USER_PB_Pin */
  GPIO_InitStruct.Pin = USER_PB_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(USER_PB_GPIO_Port, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */
  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

// movement
void moveCarStraight(double distance) {
//	distance = distance * 75;
	distance = (distance/WHEEL_CIRC_CM) * ENCODER_TPR;
	pwmVal_servo = SERVOCENTER;
//	osDelay(300);
	e_brake = 0;
	times_acceptable = 0;
	rightTarget = rightEncoderVal + distance;
	leftTarget = leftEncoderVal + distance;
	while (finishCheck());
}

void moveCarStop() {
	e_brake = 1;
	pwmVal_servo = SERVOCENTER;
	osDelay(300);
}

void moveCarRight(double angle) {
	pwmVal_servo = SERVORIGHT;
//	osDelay(300);
	e_brake = 0;
	times_acceptable = 0;
	target_angle -= angle;
	while (finishCheck());
}

void moveCarLeft(double angle) {
	pwmVal_servo = SERVOLEFT;
//	osDelay(300);
	e_brake = 0;
	times_acceptable = 0;
	target_angle += angle;
	while (finishCheck());
}

int finishCheck() {
	temp5 = times_acceptable;
	if (times_acceptable > 10) {
		pwmVal_servo = SERVOCENTER;
		e_brake = 1;
		times_acceptable = 0;
		straight_correction = 0;
		pwmVal_L = pwmVal_R = 0;
		osDelay(100);
		return 0;
	}
	return 1;
}

void testSpeed(char* buffer, int speed, int delay) {
	sprintf(buffer, "PWM: %u", speed);
	TestOLED(buffer);
	motor_set_pwm_left(speed);
	motor_set_pwm_right(speed);
	osDelay(delay);
}

void printFloat(char* buffer, double pwm) {
	sprintf(buffer, "Value: %.5f", pwm);
	TestOLED(buffer);
}

// ultrasonic
void delay(uint16_t time) {
	__HAL_TIM_SET_COUNTER(&htim12, 0);
	while (__HAL_TIM_GET_COUNTER (&htim12) < time);
}

void HCSR04_Read(void)
{
	HAL_GPIO_WritePin(TRIGGER_GPIO_Port, TRIGGER_Pin, GPIO_PIN_SET);
	delay(10);
	HAL_GPIO_WritePin(TRIGGER_GPIO_Port, TRIGGER_Pin, GPIO_PIN_RESET);
	__HAL_TIM_ENABLE_IT(&htim12, TIM_IT_CC2);
}

void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim) {
	if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_2) {
		if (Is_First_Captured == 0) {
			IC_Val1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
			Is_First_Captured = 1;
			__HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2,
					TIM_INPUTCHANNELPOLARITY_FALLING);
		} else if (Is_First_Captured == 1) {
			IC_Val2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_2);
			__HAL_TIM_SET_COUNTER(htim, 0);

			if (IC_Val2 > IC_Val1) {
				Difference = IC_Val2 - IC_Val1;
			}

			else if (IC_Val1 > IC_Val2) {
				Difference = (65535 - IC_Val1) + IC_Val2;
			}
			uDistance = Difference * .0343 / 2;
//			char str[10];
//			sprintf(str, "%u cm", uDistance);
//			TestOLED(str);

			Is_First_Captured = 0;

			__HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_2,
					TIM_INPUTCHANNELPOLARITY_RISING);
			__HAL_TIM_DISABLE_IT(&htim12, TIM_IT_CC2);
		}
	}
}

// uart debug counters
volatile uint32_t uart_rx_count = 0;    // Successfully received messages
volatile uint32_t uart_error_count = 0; // Error count

// uart receive callback - called when 5 bytes received
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART3) {
        uart_rx_count++;
        HAL_UART_Receive_IT(&huart3, aRxBuffer, 5);
    }
}

// uart error callback - handles overrun, framing, noise errors
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART3) {
        uart_error_count++;

        // Clear all error flags
        __HAL_UART_CLEAR_OREFLAG(huart);
        __HAL_UART_CLEAR_NEFLAG(huart);
        __HAL_UART_CLEAR_FEFLAG(huart);

        // Re-arm UART receive
        HAL_UART_Receive_IT(&huart3, aRxBuffer, 5);
    }
}


// encoder
// --- Wrap-safe delta helpers ---
static inline int32_t enc_delta16(uint16_t now, uint16_t prev) {
    // (now - prev) modulo 2^16, interpreted as a signed int16_t
    return (int32_t)( (int16_t)(now - prev) );
}

static inline int32_t enc_delta32(uint32_t now, uint32_t prev) {
    // (now - prev) modulo 2^32, interpreted as a signed int32_t
    return (int32_t)(now - prev);
}

// gyro
static float calibrate_bias_z(IMU_Data* imu, int n, int delay_ms) {
    float sum = 0.0f;
    for (int i = 0; i < n; ++i) {
        if (ICM20948_readGyroscope_allAxises(imu) == 0) {
            sum += imu->gyro[2];        // deg/s
        }
        osDelay(delay_ms);
    }
    return sum / (float)n;              // deg/s
}

/* USER CODE END 4 */

/* USER CODE BEGIN Header_StartDefaultTask */
/**
 * @brief  Function implementing the defaultTask thread.
 * @param  argument: Not used
 * @retval None
 */

/* USER CODE END Header_StartDefaultTask */
void StartDefaultTask(void *argument)
{
  /* USER CODE BEGIN 5 */
	/* Infinite loop */
	char str[10];
	int ccr = 10;


	pwmVal_servo = SERVOCENTER;





  /* USER CODE END 5 */
}

/* USER CODE BEGIN Header_startCommunicateTask */
/**
* @brief Function implementing the communicateTask thread.
* @param argument: Not used
* @retval None
*/
/* USER CODE END Header_startCommunicateTask */
void startCommunicateTask(void *argument)
{
  /* USER CODE BEGIN startCommunicateTask */
	char ack = 'A';

		aRxBuffer[0] = 'E'; // will store key
		aRxBuffer[1] = 'M'; // stores direction
		aRxBuffer[2] = 'P'; // 2, 3, 4 will store the magnitude, angle
		aRxBuffer[3] = 'T';
		aRxBuffer[4] = 'Y';
  /* Infinite loop */
  for(;;)
  {
	  cnt_communicate++;  // Task counter

	  magnitude = 0;
	  if ((aRxBuffer[0] == 'G' && aRxBuffer[1] == 'Y' && aRxBuffer[2] == 'R'
	  				&& aRxBuffer[3] == 'O' && aRxBuffer[4] == 'R')
	  				|| (aRxBuffer[0] == 'S' || aRxBuffer[0] == 'R'
	  						|| aRxBuffer[0] == 'L'|| aRxBuffer[0] == 'U')
	  						&& (aRxBuffer[1] == 'F' || aRxBuffer[1] == 'B')
	  						&& (0 <= aRxBuffer[2] - '0' <= 9)
	  						&& (0 <= aRxBuffer[3] - '0' <= 9)
	  						&& (0 <= aRxBuffer[4] - '0' <= 9)) {

	  			magnitude = ((int) (aRxBuffer[2]) - 48) * 100
	  					+ ((int) (aRxBuffer[3]) - 48) * 10
	  					+ ((int) (aRxBuffer[4]) - 48);

	  			if (aRxBuffer[1] == 'B') {
	  				magnitude *= -1;
	  			}

	  			switch (aRxBuffer[0]) {
	  			case 'S':
	  				moveCarStraight(magnitude);
	  				flagDone = 1;
	  				aRxBuffer[0] = 'D';
	  				aRxBuffer[1] = 'O';
	  				aRxBuffer[2] = 'N';
	  				aRxBuffer[3] = 'E';
	  				aRxBuffer[4] = '!';
	  				break;
	  			case 'R':
	  				moveCarRight(magnitude);
	  				flagDone = 1;
	  				aRxBuffer[0] = 'D';
	  				aRxBuffer[1] = 'O';
	  				aRxBuffer[2] = 'N';
	  				aRxBuffer[3] = 'E';
	  				aRxBuffer[4] = '!';
	  				break;
	  			case 'L':
	  				moveCarLeft(magnitude);
	  				flagDone = 1;
	  				aRxBuffer[0] = 'D';
	  				aRxBuffer[1] = 'O';
	  				aRxBuffer[2] = 'N';
	  				aRxBuffer[3] = 'E';
	  				aRxBuffer[4] = '!';
	  				break;
	  			case 'U':
	  				moveCarStraight(uDistance + 8-magnitude);
	  				flagDone = 1;
	  				aRxBuffer[0] = 'D';
	  				aRxBuffer[1] = 'O';
	  				aRxBuffer[2] = 'N';
	  				aRxBuffer[3] = 'E';
	  				aRxBuffer[4] = '!';
	  				break;
	  			case 'G':
	  				NVIC_SystemReset();
	  				break;
	  			}
	  		}

	  		if (flagDone == 1) {
	  			HAL_UART_Transmit(&huart3, (uint8_t*) &ack, 1, 0xFFFF);
	  			flagDone = 0;
	  		}

	  		osDelay(100);
  }
  /* USER CODE END startCommunicateTask */
}

/* USER CODE BEGIN Header_startMotorTask */
/**
* @brief Function implementing the motorTask thread.
* @param argument: Not used
* @retval None
*/
/* USER CODE END Header_startMotorTask */
void startMotorTask(void *argument)
{
  /* USER CODE BEGIN startMotorTask */
	pwmVal_R = 0;
	pwmVal_L = 0;
	int straightCorrection = 0;
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_3);
	HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_4);
	HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
	htim3.Instance->CCR1 = SERVOCENTER; //Centre

	gyro_ready = 1;  // Force bypass gyro check
	while (!gyro_ready) osDelay(1000);

	char errG[20];
	char errE[20];
  /* Infinite loop */
  for(;;)
  {
	  cnt_motor++;  // Task counter

	  static uint32_t last_ms = 0;
	  uint32_t now_ms = HAL_GetTick();
	  if (last_ms == 0) last_ms = now_ms;
	  float dt = (now_ms - last_ms) / 1000.0f;
	  if (dt <= 0.0f) dt = 1e-3f;   // guard
	  last_ms = now_ms;

	  htim3.Instance->CCR1 = pwmVal_servo;
      temp4 = pwmVal_servo;
	  if (e_brake) {
		  motor_set_pwm_left(0);
		  motor_set_pwm_right(0);
		  osDelay(1000);
		  continue;
	  }



//		printFloat(errG, (double) error_angle);

//		temp1 = pwmVal_servo;

		// left
		if (pwmVal_servo < LEFT_LIMIT) {
			temp2 = 0;
			pwmVal_R = PID_Angle(error_angle);
//			temp1 = pwmVal_R;

			pwmVal_L = pwmVal_R * (0.59);

			motor_set_pwm_right(error_angle > 0 ? pwmVal_R : -pwmVal_R);
			motor_set_pwm_left(error_angle > 0 ? pwmVal_L : -pwmVal_L);
		}

		// right
		else if (pwmVal_servo > RIGHT_LIMIT) {
			temp2 = 1;
			pwmVal_L = PID_Angle(error_angle);
			pwmVal_R = pwmVal_L * (0.59);

			motor_set_pwm_right(error_angle < 0 ? pwmVal_R : -pwmVal_R);
			motor_set_pwm_left(error_angle < 0 ? pwmVal_L : -pwmVal_L);
		}

//		if (pwmVal_servo < LEFT_LIMIT || pwmVal_servo > RIGHT_LIMIT) {
////			temp2 = 0;
//			motor_update_turn(error_angle, dt);
//		}

		// center
		else {
			temp2 = 2;
//			temp2 = rightTarget - rightEncoderVal;
//			temp1 = leftTarget - leftEncoderVal;
//			temp2 = rightTarget - rightEncoderVal;
			motor_update_straight(leftTarget, rightTarget,
			                              leftEncoderVal, rightEncoderVal, dt);
		}

		osDelay(10);

		if (times_acceptable > 1000) {
			times_acceptable = 1001;
		}
  }
  /* USER CODE END startMotorTask */
}

/* USER CODE BEGIN Header_startEncoderTask */
/**
* @brief Function implementing the encoderTask thread.
* @param argument: Not used
* @retval None
*/
/* USER CODE END Header_startEncoderTask */
void startEncoderTask(void *argument)
{
  /* USER CODE BEGIN startEncoderTask */
	HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
	HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL);
	uint32_t prevL = __HAL_TIM_GET_COUNTER(&htim2);
	uint32_t tick = HAL_GetTick();
	uint16_t prevR = (uint16_t)__HAL_TIM_GET_COUNTER(&htim4);
  /* Infinite loop */
  for(;;)
  {
	  cnt_encoder++;  // Task counter

	  if (HAL_GetTick() - tick >= 10U) {
		  uint32_t nowL = __HAL_TIM_GET_COUNTER(&htim2);
		  uint16_t nowR = (uint16_t)__HAL_TIM_GET_COUNTER(&htim4);
  //		  temp1 = d;
		  int16_t dR = enc_delta16(nowR, prevR);
		  int32_t dL = enc_delta32(nowL, prevL);   // signed ticks in last 10 ms

		  prevL = nowL;
		  prevR = nowR;
  //		  temp2 = now;

		  // TODO
		  rightEncoderVal -= dR;
		  leftEncoderVal += dL;
//		  temp4 = d;
		  tick += 10U;
	  }
	  osDelay(10);
  }
  /* USER CODE END startEncoderTask */
}

#define WARMUP_MS                300U
#define INIT_AVG_MS              300U        // initial bias average duration

// Motion detection
#define STILL_THRESH_DPS         2.0f        // if |z - bias| < this → “still”
#define STILL_GATE_MS            200U        // must stay still this long before learning bias

// Bias adaptation (slow!)
#define BIAS_TAU_SEC             10.0f       // time constant for bias learning when still

// Filtering / sanitizing
#define DEADBAND_DPS             0.5f        // zero-out tiny residual noise
#define MAX_STEP_DPS             500.0f      // reject crazy spikes between samples

// Optional overall scale trim (set to 1.0, or update after a 360° check)
static float k_scale = 1.0f;
#define GZ_SIGN (+1)

/* USER CODE BEGIN Header_startGyroTask */
/**
* @brief Function implementing the gyroTask thread.
* @param argument: Not used
* @retval None
*/
/* USER CODE END Header_startGyroTask */
static inline float wrap_deg(float a) {
    while (a > 180.0f) a -= 360.0f;
    while (a < -180.0f) a += 360.0f;
    return a;
}

typedef enum {
    TOO_RIGHT,
    TOO_LEFT
} ErrorAngle;

void startGyroTask(void *argument)
{
	(void)ICM20948_init(&imu, &hi2c2);

	// Quick initial bias average (short & simple)
	float bias = 0.0f; uint32_t n = 0;
	uint32_t next = osKernelGetTickCount();
	for (int i = 0; i < 25; ++i) {
		osDelayUntil(next += GYRO_SAMPLE_MS);
		if (ICM20948_readGyroscope_allAxises(&imu) == 0) {
			bias += (float)GZ_SIGN * imu.gyro[2];
			n++;
		}
	}
	if (n > 0) bias /= (float)n;

	gyro_ready = 1;

	// Runtime state
	total_angle = 0.0;
	uint32_t last_tick = osKernelGetTickCount();
	uint32_t still_since = 0;

	for (;;) {
		cnt_gyro++;  // Task counter

		// Periodic wakeup; absolute scheduling
		osDelayUntil(next += GYRO_SAMPLE_MS);
		uint32_t now = osKernelGetTickCount();
		float dt = (now - last_tick) * 0.001f;   // ms -> s
		last_tick = now;
		if (dt <= 0.0f) dt = GYRO_SAMPLE_MS * 0.001f; // guard

		if (ICM20948_readGyroscope_allAxises(&imu) != 0) continue;

		// Make left-turn positive
		float z_meas = (float)GZ_SIGN * imu.gyro[2];   // deg/s

		// Slow bias learn ONLY when nearly still
		float ez = z_meas - bias;
		bool still = fabsf(ez) < STILL_THRESH_DPS;
		if (still) {
			if (!still_since) still_since = now;
			else if ((now - still_since) >= STILL_GATE_MS) {
				float alpha = dt / (BIAS_TAU_SEC > 0 ? BIAS_TAU_SEC : 1.0f);
				if (alpha > 0.05f) alpha = 0.05f;      // cap if dt got large
				bias += alpha * (z_meas - bias);
			}
		} else {
			still_since = 0;
		}

		// Debiased rate + deadband
		float z_dps = z_meas - bias;
		if (fabsf(z_dps) < DEADBAND_DPS) z_dps = 0.0f;

		// Monotonic accumulation (left positive). No wrapping.
		total_angle += (double)z_dps * (double)dt;

		// Optional debug mirror
		temp3 = (float)total_angle;

		error_angle = target_angle - total_angle;

		double abs_err = fabs(error_angle);

		if (!e_brake && pwmVal_servo > LEFT_LIMIT && pwmVal_servo < RIGHT_LIMIT) {
			if (abs_err > 1) {
				straight_correction = 1;

				const int step = 5;

				// Direction sign: when (leftTarget - leftEncoderVal) < 0, keep sign (+1); else flip (-1)
				int dir_sign = ((leftTarget - leftEncoderVal) > 0) ? +1 : -1;

				// Error sign from enum
				int err_sign = 0;
				if (error_angle > 0) err_sign = -1;
				else if (error_angle < 0) err_sign = +1;

				if (err_sign != 0) {
					int delta = dir_sign * err_sign * step;     // +step or -step depending on both signs
					int cand  = (int)(SERVOCENTER) + delta;

					pwmVal_servo = cand;
				}
			} else if (straight_correction) {
				pwmVal_servo = SERVOCENTER;
				straight_correction = 0;
			};
		}
	}
}

/* USER CODE BEGIN Header_startOLEDTask */
/**
//* @brief Function implementing the OLEDTask thread.
//* @param argument: Not used
//* @retval None
//*/
///* USER CODE END Header_startOLEDTask */
//void startOLEDTask(void *argument)
//{
//  /* USER CODE BEGIN startOLEDTask */
//	uint8_t usVal[20] = { 0 };
//	uint8_t gyroVal[20] = { 0 };
//	uint8_t command[20] = { 0 };
//	uint8_t err_gyro[20] = { 0 };
//	uint8_t err_enc[20] = { 0 };
////	uint8_t temp_buf[20] = { 0 };
//
//  /* Infinite loop */
//  for(;;)
//  {
//	sprintf(usVal, "Distance: %d \0", (int) uDistance);
//	OLED_ShowString(0, 10, usVal);
//
//	int decimals = abs((int) ((error_angle - (int) (error_angle)) * 1000));
//	sprintf(gyroVal, "EGyro: %d.%d \0", (int) error_angle, decimals);
//	OLED_ShowString(0, 20, gyroVal);
//
//	decimals = abs((int) ((total_angle - (int) (total_angle)) * 1000));
//	sprintf(gyroVal, "TGyro: %d.%d \0", (int) total_angle, decimals);
//	OLED_ShowString(0, 30, gyroVal);
//
//	sprintf(command, "C: %c%c%c%c%c \0", aRxBuffer[0], aRxBuffer[1],
//			aRxBuffer[2], aRxBuffer[3], aRxBuffer[4]);
//	OLED_ShowString(0, 40, command);
//
//	sprintf(err_gyro, "errG: %.2f \0", error_angle);
//	OLED_ShowString(0, 20, err_gyro);
//	sprintf(err_enc, "errE: %.2f %.2f \0", leftTarget-leftEncoderVal, rightTarget-rightEncoderVal);
//	OLED_ShowString(0, 30, err_enc);
//
////	uint8_t temp_buf[20] = { 0 };
////	sprintf(temp_buf, "temp: %u", temp);
////	OLED_ShowString(0, 50, temp_buf);
//
//	OLED_Refresh_Gram();
//	osDelay(100);
//	OLED_Clear();
//  }
//  /* USER CODE END startOLEDTask */
//}

// Declare external counters
extern volatile uint32_t uart_rx_count;
extern volatile uint32_t uart_error_count;
extern volatile uint32_t cnt_communicate;
extern volatile uint32_t cnt_motor;
extern volatile uint32_t cnt_encoder;
extern volatile uint32_t cnt_gyro;
extern volatile uint32_t cnt_ultrasonic;

void startOLEDTask(void *argument)
{
  /* USER CODE BEGIN startOLEDTask */
	char line1[22];
	char line2[22];
	char line3[22];
	char line4[22];
	char line5[22];

  /* Infinite loop */
  for(;;)
  {
	cnt_oled++;  // Task counter

	OLED_Clear();

	// Line 1: UART RX counter and Error counter
	snprintf(line1, sizeof(line1), "RX:%lu ERR:%lu", uart_rx_count, uart_error_count);
	OLED_ShowString(0, 0, (uint8_t*)line1);

	// Line 2: Command buffer
	snprintf(line2, sizeof(line2), "BUF:%c%c%c%c%c",
			aRxBuffer[0], aRxBuffer[1], aRxBuffer[2], aRxBuffer[3], aRxBuffer[4]);
	OLED_ShowString(0, 12, (uint8_t*)line2);

	// Line 3: UART state and RXNE interrupt enable check
	// CR1 bit 5 = RXNEIE (RX Not Empty Interrupt Enable)
	uint32_t rxneie = (USART3->CR1 >> 5) & 1;
	uint32_t nvic_en = NVIC_GetEnableIRQ(USART3_IRQn);
	snprintf(line3, sizeof(line3), "RXNEIE:%lu NVIC:%lu", rxneie, nvic_en);
	OLED_ShowString(0, 24, (uint8_t*)line3);

	// Line 4: USART3 Status Register (SR)
	// Bit 5=RXNE (data ready), Bit 6=TC, Bit 7=TXE
	snprintf(line4, sizeof(line4), "SR:0x%04lX", (USART3->SR & 0xFFFF));
	OLED_ShowString(0, 36, (uint8_t*)line4);

	// Line 5: RxState and RxXferCount
	snprintf(line5, sizeof(line5), "St:0x%02X Cnt:%d",
			(unsigned int)huart3.RxState, (int)huart3.RxXferCount);
	OLED_ShowString(0, 48, (uint8_t*)line5);

	// Send periodic heartbeat to Python (every ~2 seconds)
	if (cnt_oled % 20 == 0) {
		HAL_UART_Transmit(&huart3, (uint8_t*)"HB\r\n", 4, 10);
	}

	OLED_Refresh_Gram();
	osDelay(100);
  }
  /* USER CODE END startOLEDTask */
}


/* USER CODE BEGIN Header_startUltrasonicTask */
/**
* @brief Function implementing the ultrasonicTask thread.
* @param argument: Not used
* @retval None
*/
/* USER CODE END Header_startUltrasonicTask */
void startUltrasonicTask(void *argument)
{
  /* USER CODE BEGIN startUltrasonicTask */
	HAL_TIM_IC_Start_IT(&htim12, TIM_CHANNEL_2);  // HC-SR04 Sensor
	HCSR04_Read();
	osDelay(5000);
  /* Infinite loop */
  for(;;)
  {
	  cnt_ultrasonic++;  // Task counter

	  HCSR04_Read();
	  //		if(k==1){
	  //			moveCarRight(360);
	  //			k++;
	  //		}
	  //		if (uDistance <= 15) {
		//			stopped = 1;
		//			moveCarStop();
		//			vTaskSuspend(ultrasonicTaskHandle);
		//		}

		osDelay(100);
}
  /* USER CODE END startUltrasonicTask */
}

/**
  * @brief  Period elapsed callback in non blocking mode
  * @note   This function is called  when TIM14 interrupt took place, inside
  * HAL_TIM_IRQHandler(). It makes a direct call to HAL_IncTick() to increment
  * a global variable "uwTick" used as application time base.
  * @param  htim : TIM handle
  * @retval None
  */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  /* USER CODE BEGIN Callback 0 */
  /* USER CODE END Callback 0 */
  if (htim->Instance == TIM14)
  {
    HAL_IncTick();
  }
  /* USER CODE BEGIN Callback 1 */
  /* USER CODE END Callback 1 */
}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
