import threading
from time import sleep

import database
from IoT_Cuve_controller_rpi.GPIO.core import Core

core = Core()


def waterPlant(pumpNum):
	# Turn on the pump for 10 seconds
	core._relays[pumpNum].toggle()
	sleep(10)
	core._relays[pumpNum].toggle()


def pumpControl(pumpNum):
	while True:
		# First check in the database if the linked field has anything planted, if not, sleep for 5 minutes
		# If it does, check the saved program and saved number, and water the plant accordingly
		field = database.Field.findByLinkedPump(pumpNum)
		if field.current_plant is None:
			sleep(5)
			continue
		if field.saved_prog == database.Program.HOUR:
			sleep(field.saved_number * 1)
			waterPlant(pumpNum)
		else:
			# uninplemented humidity control
			pass


def main():
	for i in range(4):
		# Create a thread for each pump
		pump = threading.Thread(target=pumpControl, args=(i,))
		pump.start()


if __name__ == '__main__':
	main()
