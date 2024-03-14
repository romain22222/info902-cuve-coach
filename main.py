import os
import sys
import subprocess
from time import sleep

import database
from IoT_Cuve_controller_rpi.GPIO.core import Core


core = Core()


def show(text: str):
	core.setText(text)


def awaitInput(text: str, availables: list[bool]) -> int:
	core.setMenuText(text, int("".join([str(1 - int(b)) for b in [availables[0], availables[3]]]), 2))
	while True:
		for i in range(len(availables)):
			if core._buttons[i].isPressed() and availables[i]:
				return i


def selector(values: list[str]) -> int:
	selected = 0
	values = values + ["BACK"]
	availables = [True for _ in range(4)]
	while True:
		choice = awaitInput(values[selected], availables)
		if choice == 0:
			selected = (selected - 1) % len(values)
		elif choice == 3:
			selected = (selected + 1) % len(values)
		elif choice == 2:
			return selected
		else:
			return -1


def badTimeCoach(plant: database.Plant):
	return f"Attention, la plante {plant.name} a besoin d'etre arrosee entre toutes les {plant.min_time_aim} et {plant.max_time_aim} heures"


def goodTimeCoach(plant: database.Plant):
	return f"Bravo, vous avez bien configure la plante {plant.name} pour etre arrosee entre toutes les {plant.max_time_aim} et {plant.max_time_aim} heures"


def coachTime(pm: database.PlantManagment, timeChoice: int, coachRepeat: bool = False) -> tuple[bool, str]:
	# Color for coach's message : light yellow
	core.setColor(255, 255, 224)
	text = ""
	# Check if the time chosen is inbetween the plant's time range
	if timeChoice < pm.plant.max_time_aim or timeChoice > pm.plant.max_time_aim:
		# If not, show the user the plant's time range
		text = badTimeCoach(pm.plant)
		if not coachRepeat:
			pm.failed_setup += 1
		return False, text
	if not coachRepeat:
		pm.success_setup += 1
	# Else, if the user has a sufficient amount of setups and the ratio of successful setups is high enough, do not show
	# (we assume the user knows the plant's time range)
	# Otherwise, congrats the user for setting up the plant and show the user the plant's time range
	if not (pm.getSetupRatio() > 0.7 and pm.getSetupTimes() > 10) or coachRepeat:
		text = goodTimeCoach(pm.plant)
	return True, text


def keyConnected() -> bool:
	try:
		ret = subprocess.check_output('sudo mount /dev/sda1 /mnt', shell=True)
	except subprocess.CalledProcessError:
		return False
	os.system('sudo umount /mnt')
	print("RESULT :"+ret)
	return "does not exist" not in ret


def getFile():
	os.system("sudo mount /dev/sda1 /mnt")
	res = None
	if os.path.exists("/mnt/profile.cuveio"):
		with open("/mnt/profile.cuveio", "r") as f:
			res = f.read().split("\n")
	os.system("sudo umount /mnt")
	return res


def getConnectedProfile() -> tuple[int, str] or None:
	# Await for the user to connect a USB key
	# If the user presses x, return None
	# When the user connects the USB key, lookup the file "profile.cuveio" stored somewhere in the key
	# If the file is not found, return None
	# If the file is found, return the user's id and the stored password

	# Color for USB key's connection : light blue
	core.setColor(173, 216, 230)
	core.setMenuText("Inserez la cle", 3)
	while not core.getCancelButton().isPressed():
		# Check if a USB key is connected
		if keyConnected():
			# Check if the file "profile.cuveio" is present in the key
			f = getFile()
			if f is not None:
				# Return the user's id and the stored password
				return [int(f[0]), f[1]]
			else:
				# Show a message to the user
				show("Profil absent")
				return None
	show("Annule")
	return None


def getProfileId() -> int:
	file = getConnectedProfile()
	if file is None:
		return -1
	profile = database.User.findById(file[0])
	storedPassword = file[1]
	if storedPassword != profile.password:
		show("La cle du compte est invalide")
		return -1
	return profile.id


def selectField() -> database.Field:
	# Color for field's selection : brown
	core.setColor(139, 69, 19)
	fields = database.Field.getAllFields()
	selected = selector(
		[f"{f.id}:{f.current_plant.name.upper() if f.current_plant else 'EMPTY'};p:{f.linked_pump}" for f in
		 fields])
	if selected in (-1, len(fields)):
		return None
	return fields[selected]


def selectPlant() -> database.Plant:
	# Color for plant's selection : light green
	core.setColor(144, 238, 144)
	plants = database.Plant.getAllPlants()
	selected = selector([f"{p.id}:{p.name.upper()}" for p in plants] + ["EMPTY"])
	if selected in (-1, len(plants) + 1):
		return None
	if selected == len(plants):
		return database.Plant(-1, "EMPTY", 0, 0, 0, 0)
	return plants[selected]


def selectTiming() -> int:
	# Color for timing's selection : light blue
	core.setColor(173, 216, 230)
	timing = 0
	availables = [True for _ in range(4)]
	while True:
		availables[0] = timing > 0
		ret = awaitInput(f"Water freq: {timing}h", availables)
		if ret == 0:
			timing -= 1
		elif ret == 3:
			timing += 1
		elif ret == 2:
			return timing
		else:
			return -1


def validateSetup() -> bool:
	# Color for validation : yellow
	core.setColor(255, 255, 0)
	return awaitInput("Validate ?", [True, True, True, False])


def main():
	"""
	1. Get the user's profile
	2. Select the field the user wants to edit or exit
	3. Get the plant the user wants to plant there
	4. Select how often the user wants to water the plant
	5. Check with the coach if the time is good
	6. Either validate the time (if in the range) or ask the user to select another time or repeat the coach
	7. Save the setup in the database
	8. Repeat from step 2
	"""

	user = database.User.findById(getProfileId())
	if user is None:
		sleep(5)
		return
	show(f"Bonjour {user.username}")
	sleep(2)
	state = 0
	plant: database.Plant = None
	field: database.Field = None
	timing = -1
	force = False
	while True:
		if state == 0:
			field = selectField()
			if field is None:
				break
			state = 1
		elif state == 1:
			plant = selectPlant()
			if plant is None:
				state = 0
				continue
			if plant.id == -1:
				plant = None
				timing = -1
				state = 4
				continue
			state = 2
		elif state == 2:
			timing = selectTiming()
			if timing == -1:
				state = 1
				continue
			state = 3
		elif state == 3:
			pm = database.PlantManagment.findByUserAndPlant(user.id, plant.id)
			ret = coachTime(pm, timing, force)
			state += 2 * int(ret[0]) - 1
			pm.save()
			force = False
			awaitInput(ret[1], [True for _ in range(4)])
		elif state == 4:
			out = validateSetup()
			if out == 0:
				if plant is None:
					state = 0
					continue
				force = True
				state = 3
			elif out == 1:
				state = 2
			elif out == 2:
				field.current_plant = plant
				field.saved_prog = database.Program.HOUR
				field.saved_number = timing
				field.save()
				state = 0


if __name__ == '__main__':
	if "keyTest" in sys.argv:
		print(keyConnected())
		print(getFile())
		exit(0)
	if "test" in sys.argv:
		keyConnected = lambda: True
		getFile = lambda: ("1", "0683207903f1832a87e488645fe0761354701afd028a2d7fadb8131bb8f96a67")
	main()
	if "test" not in sys.argv:
		core.quit()
