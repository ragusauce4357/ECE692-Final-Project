# PCB for Logic Analyzer

This will hold a PCB design for our logic analyzer. We're yet to decide whether we're going to do a complete PCB design, microcontroller and all, or just a 'shield' which connects to the morpho connectors. Regardless, those are the only two options... we will definitely need the USB 2.0 connection which the nucleo board itself doesn't directly provide. Below are our options. All prices are ballpark ofc.

## **Option 1:** Morpho Connector Shield

- If we take this option, we will only need to make a *shield* which goes on top of the existing STM32 microcontroller. This shield will have:
	- Male connectors, to connect to the morpho header pins on the STM32.
	- A 12 pin 90 degree male connector, hanging off the edge of the board. These will be the exposed 8 channels + 2 bxCAN + 2 grounds. The 8 channels will connect to pins PC1 to PC8 respectively, and CAN TX and RX to PB9 and PB8 respectively.
	- A USB connection, with DP on PA12, DM on PA11, VBUS connected to the 5V rail as well as PA9, and PA8 is also involved somehow, but idk how.
	- A level shifter, for the 8 channels (Bryan already got this)
- The budgeting will be:
	- Since this is a 2 layer board, the PCB alone will be either:
		- **$15** ($7 PCB, $8 shipping) if we opt for 24h fab time, but standard delivery (usually takes 10-14 days; need to order pronto)
		- **$30** ($7 PCB, $23 shipping) if we opt for 24h fab time, with DHL shipping 2-4 days. We will get the boards in a week or less after ordering if we do this.
	- Other parts from digikey/amazon:
		- **$5** Connectors. Although there's a high chance someone/somewhere on campus has this that we can permanently borrow :eyes:
		- **$2** USB connector. Chances are we'll definitely have to buy this from Digikey, unless someone on campus has some.
		- **$7** Digikey shipping. Applies unless we order off amazon.
	- So in total: **$30-45**. This will yield 5 completed boards, and is the lowest risk option, probably best for our case.
- Designing and ordering this pcb should be easy enough; we should be able to do it within a day.

## **Option 2:** Custom Board

- If we take this option, we'll have to do everything from the other option, plus the microcontroller itself, an LDO to convert the 5V from VBUS to 3v3 for the stm, crystal oscillators, status LEDs, etc. Stuff we'll need:
	- All the components from option 1
	- Capacitors, resistors, LEDs, crystals, and LDO.
	- 5x stm chips.
- The budgeting will be:
	- **$15 - $30** PCB costs are the same 
	- **$0** I have a few passive components and LDOs we can use 
	- **$16** Combined cost of components from option 1
	- **$40** 5x f446's from Digikey. We could also make just 2 or 3, which will lower the price.
	- In total for option 2: **$70-$85**. This will also yield 5 completed boards. There is higher risk, but it also grants us freedom to design it the way we want; form-factor, shape, etc.
- Designing and ordering this pcb will likely take 2-3 days.
