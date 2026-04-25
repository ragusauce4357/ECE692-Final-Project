/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "usb_device.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "usbd_cdc_if.h"
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
CAN_HandleTypeDef hcan1;

TIM_HandleTypeDef htim1;
DMA_HandleTypeDef hdma_tim1_up;

UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
#define DATA_CHUNK 512
#define DMA_BUF_SIZE (DATA_CHUNK*2) // 1024 uint16 elements, 2048 bytes in RAM

//The DMA will dump the GPIO samples here
//I'm using the ping-pong idea we talked about but with the circular array
//So we have one array of 1024 uint16_t elements holding 2 chunks of 512 samples
//Each sample is 2 bytes (uint16_t) so the total buffer is 2048 bytes in memory

//Basically, when the USB is transmitting, new samples still need somewhere to go
//So the idea is, when the DMA is half full, the USB can transmit samples
//from position 0 while new samples get written to position 512 and onward.
uint16_t dma_buf[DMA_BUF_SIZE];
static uint8_t logic_seq_num = 0;
static uint8_t can_seq_num = 0;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_TIM1_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_CAN1_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

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
  MX_DMA_Init();
  MX_TIM1_Init();
  MX_USART2_UART_Init();
  MX_USB_DEVICE_Init();
  MX_CAN1_Init();
  /* USER CODE BEGIN 2 */
  // We'll use the bxCAN peripheral for CAN
  // The thing is tho, it rejects everything by default.
  // So the filter below lets it know which data to let in
  //printf("Hello World"); debug statement
  CAN_FilterTypeDef canFilter;

  canFilter.FilterBank = 0; //Bank 0
  canFilter.FilterMode = CAN_FILTERMODE_IDMASK;
  canFilter.FilterScale = CAN_FILTERSCALE_32BIT;
  canFilter.FilterIdHigh = 0x0000;
  canFilter.FilterIdLow = 0x0000;
  canFilter.FilterMaskIdHigh = 0x0000;
  canFilter.FilterMaskIdLow = 0x0000;
  canFilter.FilterFIFOAssignment = CAN_RX_FIFO0;
  canFilter.FilterActivation = ENABLE;

  if (HAL_CAN_ConfigFilter(&hcan1, &canFilter) != HAL_OK)
  {
    Error_Handler();
  }

  HAL_CAN_Start(&hcan1);

  //Fires an RX interrupt when a frame arrives in the receive FIFO
  HAL_CAN_ActivateNotification(&hcan1, CAN_IT_RX_FIFO0_MSG_PENDING);

  //To let the USB breathe
  HAL_Delay(1000);
  //Start TIM1 - 1MHz for DMA sampling
  HAL_TIM_Base_Start(&htim1);

  //Start DMA - reads the GPIOC -> IDR into dma_buf on every TIM1 tick, so 1us
  HAL_DMA_Start_IT(&hdma_tim1_up, (uint32_t)&GPIOC->IDR,
		          (uint32_t)dma_buf, DMA_BUF_SIZE);

  //Enable the DMA request on TIM1 update event
  TIM1-> DIER |= TIM_DIER_UDE;
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
	  	/* Testing Code
	    // Toggle the Green LED (PA5) so we have a signal to "sniff"
	    HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);

	    // Create and send a test CAN message to ourselves
	    CAN_TxHeaderTypeDef txHeader;
	    uint8_t testData[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE};
	    uint32_t txMailbox;

	    txHeader.StdId = 0x123;
	    txHeader.RTR = CAN_RTR_DATA;
	    txHeader.IDE = CAN_ID_STD;
	    txHeader.DLC = 8;

	    HAL_CAN_AddTxMessage(&hcan1, &txHeader, testData, &txMailbox);

	    // Wait half a second
	    HAL_Delay(2000);
		*/
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
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
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 4;
  RCC_OscInitStruct.PLL.PLLN = 168;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = 7;
  RCC_OscInitStruct.PLL.PLLR = 2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief CAN1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_CAN1_Init(void)
{

  /* USER CODE BEGIN CAN1_Init 0 */

  /* USER CODE END CAN1_Init 0 */

  /* USER CODE BEGIN CAN1_Init 1 */

  /* USER CODE END CAN1_Init 1 */
  hcan1.Instance = CAN1;
  hcan1.Init.Prescaler = 6;
  hcan1.Init.Mode = CAN_MODE_NORMAL;
  hcan1.Init.SyncJumpWidth = CAN_SJW_1TQ;
  hcan1.Init.TimeSeg1 = CAN_BS1_11TQ;
  hcan1.Init.TimeSeg2 = CAN_BS2_2TQ;
  hcan1.Init.TimeTriggeredMode = DISABLE;
  hcan1.Init.AutoBusOff = ENABLE;
  hcan1.Init.AutoWakeUp = DISABLE;
  hcan1.Init.AutoRetransmission = ENABLE;
  hcan1.Init.ReceiveFifoLocked = DISABLE;
  hcan1.Init.TransmitFifoPriority = DISABLE;
  if (HAL_CAN_Init(&hcan1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN CAN1_Init 2 */

  /* USER CODE END CAN1_Init 2 */

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

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 0;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = 167;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
  if (HAL_TIM_Base_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA2_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA2_Stream5_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA2_Stream5_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA2_Stream5_IRQn);

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
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(Status_LED_GPIO_Port, Status_LED_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : Status_LED_Pin */
  GPIO_InitStruct.Pin = Status_LED_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(Status_LED_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pins : Channel_1_Pin Channel_2_Pin Channel_3_Pin Channel_4_Pin
                           Channel_5_Pin Channel_6_Pin Channel_7_Pin Channel_8_Pin */
  GPIO_InitStruct.Pin = Channel_1_Pin|Channel_2_Pin|Channel_3_Pin|Channel_4_Pin
                          |Channel_5_Pin|Channel_6_Pin|Channel_7_Pin|Channel_8_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pin : LD2_Pin */
  GPIO_InitStruct.Pin = LD2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

//For sending words over UART
//int __io_putchar(int ch) {
//  HAL_UART_Transmit(&huart2, (uint8_t *)&ch, 1, 0xFFFF);
//  return ch;
//}

// Fires when DMA has filled the buffer with 512 samples (1024 bytes)
// Sends the raw samples over USB to PC where our Go and Python apps will take over
// CDC_Transmit_FS handles splitting into 64 byte USB transactions internally
// We just pass the full 1028 byte packet and the USB stack takes care of it
// Format: [0xAA][0xBB][seq#][512 uint16 samples=1024 bytes][checksum]
void send_logic_packet(uint16_t *data_ptr)
{
	//made this static so it persists during USB transfer
	static uint8_t packet[1028]; // 3 header + 1024 data + 1 checksum
	packet[0] = 0xAA;
	packet[1] = 0xBB;
	packet[2] = logic_seq_num++;

	//I found that memcpy works much faster than a typical for loop
	//it's optimized at the hardware level
	memcpy(&packet[3], data_ptr, DATA_CHUNK*2);

    uint8_t checksum = 0;
	for (int i = 0; i < 1027; i++) {
		checksum ^= packet[i];
	}
	packet[1027] = checksum;

	//Monitor for overflows here!
	if (CDC_Transmit_FS(packet, 1028) != USBD_OK)
	{
		//This means that the PC isn't reading fast enough
	    static uint32_t dropped_packets = 0;
	    dropped_packets++;
	}
}
void HAL_DMA_XferHalfCpltCallback(DMA_HandleTypeDef *hdma) {
    if (hdma == &hdma_tim1_up) {
    	send_logic_packet(&dma_buf[0]);
    }
}

void HAL_DMA_XferCpltCallback(DMA_HandleTypeDef *hdma) {
    if (hdma == &hdma_tim1_up) {
    	send_logic_packet(&dma_buf[DATA_CHUNK]);
    }
}

// Fires when a complete CAN frame arrives in the bxCAN receive FIFO
// Packages decoded frame and sends over USB
// Format: [0xCC][0xDD][seq#][ID_HIGH][ID_LOW][DLC][data][checksum]
void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan) {
    CAN_RxHeaderTypeDef rxHeader;
    uint8_t rxData[8];

    if (HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &rxHeader, rxData) == HAL_OK) {

        // CAN packet uses different header so Go or C/C++ can distinguish it
    	// We need to take this into acc for the Go or C/C++ program
    	// for ID_HIGH
    	// if the ID is like 0x123
    	// ID_HIGH would be 0x01 and ID_LOW will be 0x23
        static uint8_t packet[15];
        // CAN header byte 1
        packet[0] = 0xCC;

        // CAN header byte 2
        packet[1] = 0xDD;

        // sequence number
        packet[2] = can_seq_num++;

        // CAN ID high byte
        packet[3] = (rxHeader.StdId >> 8) & 0xFF;

        // CAN ID low byte
        packet[4] = rxHeader.StdId & 0xFF;

        // data length code - just how many data bytes are in the CAN frame
        packet[5] = rxHeader.DLC;

        for (int i = 0; i < rxHeader.DLC; i++) {
            packet[i+6] = rxData[i];
        }

        // Checksum over everything except checksum byte itself
        uint8_t checksum = 0;
        uint8_t packet_len_b4_checksum = 6 + rxHeader.DLC;
        for (int i = 0; i < packet_len_b4_checksum; i++) {
            checksum ^= packet[i];
        }

        //putting checksum right after last data byte
        packet[packet_len_b4_checksum] = checksum;

        //total bytes to send:
        //Headers(2) + Seq(1) + ID(2) + DLC(1) + Data(DLC) + checksum(1)
        // Total is 7 + DLC
        CDC_Transmit_FS(packet, 7 + rxHeader.DLC);
    }
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
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
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
