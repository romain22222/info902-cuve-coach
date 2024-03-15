import threading
from time import sleep

import database
from IoT_Cuve_controller_rpi.GPIO.core import Core


def waterPlant(pumpNum):
	print("watering with pump", pumpNum)
	# Turn on the pump for 10 seconds
	core._relays[pumpNum].toggle()
	sleep(1)  # Should be 10s
	core._relays[pumpNum].toggle()
	print("done watering with pump", pumpNum)


def pumpControl(pumpNum):
	sleep(pumpNum * .1)  # padding to avoid bdd access at the same time while still having a single connexion
	while True:
		# First check in the database if the linked field has anything planted, if not, sleep for 5 minutes
		# If it does, check the saved program and saved number, and water the plant accordingly
		field = database.Field.findByLinkedPump(pumpNum)
		print("Pump", pumpNum, "field", field.id, field.current_plant,
			  field.current_plant.name if field.current_plant is not None else None)
		if field.current_plant is None:
			sleep(5)  # Should be 5 minutes
			continue
		if field.saved_prog == database.Program.HOUR:
			sleep(field.saved_number * 1)  # Should be 1 hour times the saved number
			waterPlant(pumpNum)
		else:
			# uninplemented humidity control
			pass


def main():
	try:
		pumps = []
		for i in range(4):
			# Create a thread for each pump
			pumps.append(threading.Thread(target=pumpControl, args=(i,), daemon=True))
			pumps[-1].start()
		# Wait for all threads to finish
		for p in pumps:
			p.join()
	except KeyboardInterrupt:
		core.quit()
		exit(0)


if __name__ == '__main__':
	core = Core()
	main()
