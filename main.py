import sys
import database


class Core:
	class Button:
		def isPressed(self) -> bool:
			...

		def isChanged(self) -> bool:
			...

	class LCD:
		def setText(self, text: str):
			...

		def setText_noRefresh(self, text: str):
			...

		def setText_defil(self, text: str):
			...

		def setMenuText(self, setup: int):
			...

	class RGBLCD(LCD):
		def setRGB(self, r: int, g: int, b: int):
			...

	class Relais:
		def on(self):
			...

		def off(self):
			...

		def toggle(self):
			...

	lcd = RGBLCD()
	relais = [Relais() for _ in range(4)]
	buttons = [Button() for _ in range(4)]


def show(text: str):
	if len(text) > 16:
		Core.lcd.setText_defil(text)
	else:
		Core.lcd.setText(text)


def awaitInput(availables: list[bool]) -> int:
	Core.lcd.setMenuText(int("".join([str(1 - int(b)) for b in [availables[0], availables[3]]]), 2))
	while True:
		for i in availables:
			if Core.buttons[i].isPressed() and availables[i]:
				return i


def selector(values: list[str]) -> int:
	selected = 0
	values = values + ["BACK"]
	availables = [True for _ in range(4)]
	show(values[0])
	while True:
		choice = awaitInput(availables)
		match choice:
			case 0:
				selected = (selected - 1) % len(values)
			case 3:
				selected = (selected + 1) % len(values)
			case 2:
				return selected
			case _:
				return -1
		Core.lcd.setText(values[selected])


def badTimeCoach(plant: database.Plant):
	show(
		f"Attention, la plante {plant.name} a besoin d'être arrosée entre toutes les {plant.min_time_aim} et {plant.max_time_aim} heures")


def goodTimeCoach(plant: database.Plant):
	show(
		f"Bravo, vous avez bien configuré la plante {plant.name} pour être arrosée entre toutes les {plant.max_time_aim} et {plant.max_time_aim} heures")


def coachTime(pm: database.PlantManagment, timeChoice: int, coachRepeat: bool = False) -> bool:
	# Color for coach's message : light yellow
	Core.lcd.setRGB(255, 255, 224)
	# Check if the time chosen is inbetween the plant's time range
	if timeChoice < pm.plant.max_time_aim or timeChoice > pm.plant.max_time_aim:
		# If not, show the user the plant's time range
		badTimeCoach(pm.plant)
		if not coachRepeat:
			pm.failed_setup += 1
		return False
	if not coachRepeat:
		pm.success_setup += 1
	# Else, if the user has a sufficient amount of setups and the ratio of successful setups is high enough, do not show
	# (we assume the user knows the plant's time range)
	# Otherwise, congrats the user for setting up the plant and show the user the plant's time range
	if not (pm.getSetupRatio() > 0.7 and pm.getSetupTimes() > 10) or coachRepeat:
		goodTimeCoach(pm.plant)
	return True


def getProfileId() -> int:
	# TODO : code to get the user's profile
	return "1"


def selectField() -> database.Field:
	# Color for field's selection : brown
	Core.lcd.setRGB(139, 69, 19)
	fields = database.Field.getAllFields()
	selected = selector([f"{f.id}:{f.current_plant.name.upper() if f.current_plant else 'EMPTY'};p:{f.linked_pump}" for f in
						fields])
	if selected in (-1, len(fields)):
		return None
	return fields[selected]


def selectPlant() -> database.Plant:
	# Color for plant's selection : light green
	Core.lcd.setRGB(144, 238, 144)
	plants = database.Plant.getAllPlants()
	selected = selector([f"{p.id}:{p.name.upper()}" for p in plants])
	if selected in (-1, len(plants)):
		return None
	return plants[selected]


def selectTiming() -> int:
	# Color for timing's selection : light blue
	Core.lcd.setRGB(173, 216, 230)
	timing = 0
	show(f"Water freq: {timing}h")
	availables = [True for _ in range(4)]
	while True:
		availables[0] = timing > 0
		match awaitInput(availables):
			case 0:
				timing -= 1
			case 3:
				timing += 1
			case 2:
				return timing
			case _:
				return -1
		show(f"Water freq: {timing}h")


def validateSetup() -> bool:
	# Color for validation : yellow
	Core.lcd.setRGB(255, 255, 0)
	show("Validate ?")
	return awaitInput([True, True, True, False])


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
	state = 0
	plant: database.Plant = None
	field: database.Field = None
	timing = -1
	pm: database.PlantManagment = None
	force = False
	while True:
		match state:
			case 0:
				field = selectField()
				if field is None:
					break
				state = 1
			case 1:
				plant = selectPlant()
				if plant is None:
					state = 0
					continue
				state = 2
			case 2:
				timing = selectTiming()
				if timing == -1:
					state = 1
					continue
			case 3:
				pm = database.PlantManagment.findByUserAndPlant(user.id, plant.id)
				state += 2 * coachTime(pm, timing, force) - 1
				pm.save()
				force = False
				awaitInput([True for _ in range(4)])
			case 4:
				out = validateSetup()
				match out:
					case 0:
						force = True
						state = 3
					case 1:
						state = 2
					case 2:
						field.current_plant = plant
						field.saved_prog = database.Program.HOUR
						field.saved_number = timing
						field.save()
						state = 0


if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == "test":
		show = lambda x: print("SHOW : " + x)
		awaitInput = lambda: input("INPUT : ")
	main()
