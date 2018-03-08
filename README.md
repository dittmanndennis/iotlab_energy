IoT-LAB Energy Consumption Experiment
=====================================

The Contiki based test program cycles through various power consumption states, including the different transceiver states with different transmission powers. It starts with a synchronization sequence for an easier analysis.

1. Setup a working directory

    ```
    mkdir ~/energyexperiment/
    ```

2. Download and initialize the IoT-LAB Contiki version.
	
    ```
    cd ~/energyexperiment/
    mkdir contiki
    cd contiki
    git clone https://github.com/iot-lab/iot-lab
    cd iot-lab
    make setup-contiki
    ```

3. Clone this repository

    ```
    cd ~/energyexperiment/
    git clone https://github.com/koalo/iotlab_energy
    cd iotlab_energy
    ```

4. Optional: If you have downloaded Contiki to another location, adapt the CONTIKI path in the Makefile.

5. Build 

    ```
    make TARGET=iotlab-m3
    ```
	
6. Install the IoT-LAB CLI tools
	
    https://github.com/iot-lab/iot-lab/wiki/CLI-Tools-Installation

7. Authenticate to the IoT-LAB
   
    ```
    iotlab-auth -u [your_username]
    ```

8. Create an energy measurement profile

    ```
    iotlab-profile addm3 -n energymeasurement -current -voltage -power -period 140 -avg 4
    ```

9. Start an experiment

    ```
    iotlab-experiment submit -d 10 -l lyon,m3,10,energy.iotlab-m3,energymeasurement
    ```

10. Wait until the experiment is finished

    ```
    iotlab-experiment wait --state Terminated
    ```

11. Get the results 

    ```
    scp [your_username]@lyon.iot-lab.info:~/.iot-lab/last/consumption/m3-10.oml ./
    ```
    
12. Parse the results

    ```
    ./parse.py m3-10.oml
    ```

Results
-------

```
Idle Power 126 mW
Idle Current 38 mA

           casetxt power_extra current_extra power_total current_total
case                                                                  
9        Green LED        8 mW          3 mA      134 mW         41 mA
10      Yellow LED        8 mW          3 mA      134 mW         41 mA
11         Red LED        9 mW          3 mA      135 mW         41 mA
12            Idle        0 mW          0 mA      126 mW         38 mA
14         TRX_OFF        3 mW          1 mA      129 mW         39 mA
15          PLL_ON       20 mW          6 mA      146 mW         45 mA
16           RX_ON       43 mW         13 mA      169 mW         52 mA
17     TX TX_PWR 0       49 mW         15 mA      175 mW         54 mA
18     TX TX_PWR 1       48 mW         15 mA      174 mW         53 mA
19     TX TX_PWR 2       47 mW         14 mA      173 mW         53 mA
20     TX TX_PWR 3       45 mW         14 mA      172 mW         52 mA
21     TX TX_PWR 4       44 mW         14 mA      170 mW         52 mA
22     TX TX_PWR 5       43 mW         13 mA      169 mW         52 mA
23     TX TX_PWR 6       42 mW         13 mA      168 mW         51 mA
24     TX TX_PWR 7       39 mW         12 mA      165 mW         50 mA
25     TX TX_PWR 8       38 mW         12 mA      164 mW         50 mA
26     TX TX_PWR 9       37 mW         11 mA      163 mW         50 mA
27    TX TX_PWR 10       36 mW         11 mA      162 mW         49 mA
28    TX TX_PWR 11       33 mW         10 mA      159 mW         49 mA
29    TX TX_PWR 12       32 mW         10 mA      158 mW         48 mA
30    TX TX_PWR 13       30 mW          9 mA      156 mW         48 mA
31    TX TX_PWR 14       29 mW          9 mA      155 mW         47 mA
32    TX TX_PWR 15       27 mW          8 mA      153 mW         47 mA
```
