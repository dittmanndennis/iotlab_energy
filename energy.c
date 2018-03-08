#include "platform.h"
#include "../../../../openlab/periph/rf2xx.h"
#include "../../../../openlab/periph/l3g4200d.h"

#include "contiki.h"
#include <stdio.h>

#include "dev/leds.h"

#define SYNC_SEQUENCE 22
#define CASE_DURATION 5 // seconds

extern rf2xx_t RF2XX_DEVICE;

void enter_tx(int power) {
  // Disable interrupt
  rf2xx_irq_disable(RF2XX_DEVICE);

  // Step 1: RESET
  rf2xx_reset(RF2XX_DEVICE);
  rf2xx_wakeup(RF2XX_DEVICE);

  // Step 2: Set IRQ mask PLL ON
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__IRQ_MASK,
          RF2XX_IRQ_STATUS_MASK__PLL_LOCK);
  rf2xx_reg_read(RF2XX_DEVICE, RF2XX_REG__IRQ_STATUS);

  // Step 3: disable TX_AUTO_CRC_ON
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__TRX_CTRL_1, 0);

  // Step 4: Set State TRX_OFF
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__TRX_STATE,
          RF2XX_TRX_STATE__FORCE_TRX_OFF);

  // Step 5: Set clock at pin 17
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__TRX_CTRL_0, 0x01);

  // Step 6: Set tx_channel
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__PHY_CC_CCA,
          RF2XX_PHY_CC_CCA_DEFAULT__CCA_MODE | 14);

  // Step 7: Set output power as specified
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__PHY_TX_PWR, power);
  power = (power + 1) % 0x10; // increment for next time

  // Step 8: Verify TRX_OFF status
  rf2xx_reg_read(RF2XX_DEVICE, RF2XX_REG__TRX_STATUS);

  // Step 9: Enable continuous transmission test mode step #1
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__TST_CTRL_DIGI, 0x0F);

  // Step 10: not used for PRBS
  rf2xx_reg_write(RF2XX_DEVICE, 0x0C, 0x03);

  // Step 11: idem
  rf2xx_reg_write(RF2XX_DEVICE, 0x0A, 0xA7);

  // Step 12: Write a complete frame buffer with random data
  uint8_t frame_buf[128];
  uint16_t i;
  // Set length
  frame_buf[0] = 127;

  // Set data to send
  for (i = 1; i < 128; i++)
  {
      /*
       * If data is all zero or all one, (0x00 or 0xFF), then a sine wave
       * will be continuously transmitted (fc-0.5 MHz or fc+0.5MHz resp.)
       *
       * If normal modulated data is desired, random data should fill the
       * buffer (with rand() for example)
       */
      frame_buf[i] = rand(); /* Modulated data */
  }

  // Write data
  rf2xx_fifo_write(RF2XX_DEVICE, frame_buf, 128);

  // Step 13: Enable continuous transmission test mode step #2
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__PART_NUM, 0x54);

  // Step 14: Enable continuous transmission test mode step #3
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__PART_NUM, 0x46);

  // Step 15: Enable PLL_ON state
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__TRX_STATE, RF2XX_TRX_STATE__PLL_ON);

  // Step 16: Wait for PLL_LOCK
  while (!rf2xx_reg_read(RF2XX_DEVICE, RF2XX_REG__IRQ_STATUS)
          & RF2XX_IRQ_STATUS_MASK__PLL_LOCK)
  {
      asm volatile("nop");
  }

  // Step 17: Enter BUSY TX
  rf2xx_reg_write(RF2XX_DEVICE, RF2XX_REG__TRX_STATE, RF2XX_TRX_STATE__TX_START);
}

PROCESS(consumption_profile, "Led blinking");
AUTOSTART_PROCESSES(&consumption_profile);

PROCESS_THREAD(consumption_profile, ev, data)
{
  PROCESS_BEGIN();
  static struct etimer timer;
  static int i = 0;
  static int sync = SYNC_SEQUENCE;
  static int power;

  etimer_set(&timer, CLOCK_SECOND*CASE_DURATION);

  while(1) {
    PROCESS_WAIT_EVENT();
    if (ev == PROCESS_EVENT_TIMER) {
      etimer_restart(&timer);
      i++;
      
      printf("Case %d\n", i);
      if(i <= 8) {
        if(sync & 0x80) {
          leds_on(LEDS_ALL);
          enter_tx(0);
        }
        else {
          leds_off(LEDS_ALL);
          rf2xx_sleep(RF2XX_DEVICE);
        }
        sync <<= 1;
      }
      else {
        switch(i) {
        case 9:
          rf2xx_sleep(RF2XX_DEVICE);
          leds_on(LEDS_GREEN);
          leds_off(LEDS_YELLOW);
          leds_off(LEDS_RED);
          break;
        case 10:
          leds_off(LEDS_GREEN);
          leds_on(LEDS_YELLOW);
          leds_off(LEDS_RED);
          break;
        case 11:
          leds_off(LEDS_GREEN);
          leds_off(LEDS_YELLOW);
          leds_on(LEDS_RED);
          break;
        case 12:
          leds_off(LEDS_GREEN);
          leds_off(LEDS_YELLOW);
          leds_off(LEDS_RED);
          break;
        case 13:
          //l3g4200d_powerdown();
          printf("ctrl reg %i\n",l3g4200d_read_crtl_reg(1));
          break;
        case 14:
          rf2xx_wakeup(RF2XX_DEVICE);
          break;
        case 15:
          rf2xx_set_state(RF2XX_DEVICE, RF2XX_TRX_STATE__PLL_ON);
          break;
        case 16:
          rf2xx_set_state(RF2XX_DEVICE, RF2XX_TRX_STATE__RX_ON);
          break;
        default:
          power = i - 17;
          printf("Power %i\n",power);
          enter_tx(power);
          if(power == 0xF) {
            i = 0;
            sync = SYNC_SEQUENCE;
          }
          break;
        }
      }
    }
  }
  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
