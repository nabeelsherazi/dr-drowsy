# Dr. Drowsy

Drowsiness detection glasses for doctors and other professionals in attention-critical fields.

# About

This software was written as part of a semester project for EECE 4512 Healthcare Technologies: Sensors, Systems, and Analysis at Northeastern University in Spring 2019. It ran on an Adafruit Trinket M0 board, with CircuitPython v3.11 installed. Mounted on a pair of standard lab glasses, the objective of the device was to detect drowsiness in the wearer, and alert them of their incapacitated state if so. While this was accomplished in the prototype device with a blue LED, it could easily be expanded to a network connected report that would alert a central system, or supervisor.

![Image of Dr. Drowsy prototype device](https://raw.githubusercontent.com/nabeelsherazi/dr-drowsy/master/docs/glasses.png)

You can read more about the device in the full engineering report we submitted for the class, available in `./docs/Solution Report`.

# Software

Detailed description of the software and its architecture, written by Nabeel Sherazi, are available in the solution report above. Two versions of the software are given. In the master branch is the version of the software that actually ran on the device, using optimization techniques to obtain the fastest possible code given the memory constraints of the Trinket M0 device. In the alternate branch is the old version of the code, written using conventional object-oriented techniques. While this version had to be scrapped due to it having too much overhead to run, it would still be able to run on more powerful devices, and its readability may be helpful in understanding what the code is doing.

Below is an excerpted figure from the solution report which summarized the control flow of the software.

![Flow chart of the software architecture in Dr. Drowsy](https://raw.githubusercontent.com/nabeelsherazi/dr-drowsy/master/docs/architecture.png)

# Copyright & License

This software remains copyright of Nabeel Sherazi, Olivia Hagedorn, Harmony Chen, and Khoy Young, affiliated with Northeastern University at the time of its development. It made open source under a GPL license.

Acknowledgement is given to [Matt Dailis](https://github.com/mattdailis) for his invaluable advice in embedded programming techniques.
