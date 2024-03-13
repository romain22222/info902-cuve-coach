import sys
from enum import Enum
from typing import List, Self
import mysql.connector

conn = mysql.connector.connect(
	host="localhost",
	user="your_username",
	password="your_password",
	database="your_database"
)

cursor = conn.cursor()


def doCommand(command: str):
	cursor.execute(command)
	return cursor.fetchall()


"""
Database structure:
Table fields {
	id integer [primary key]
	current_plant integer
	saved_prog integer [note: "1: each X hours, 2: aiming humidity X kPa"]
	saved_number integer
	linked_pump integer
}

Table plants {
	id integer [primary key]
	name text
	min_time_aim integer
	max_time_aim integer
	min_humidity integer
	max_humidity integer
}

Table users {
	id integer [primary key]
	username text
}

Table plant_managment {
	user_id integer
	plant_id integer
	success_setup integer
	failed_setup integer
}


Ref: users.id < plant_managment.user_id
Ref: plants.id < fields.current_plant
Ref: plants.id < plant_managment.plant_id

"""


def init(fullReload: bool):
	if fullReload:
		doCommand("DROP TABLE IF EXISTS fields")
		doCommand("DROP TABLE IF EXISTS plants")
		doCommand("DROP TABLE IF EXISTS users")
		doCommand("DROP TABLE IF EXISTS plant_managment")
		doCommand(
			"CREATE TABLE IF NOT EXISTS fields (id INTEGER PRIMARY KEY, current_plant INTEGER, saved_prog INTEGER, saved_number INTEGER, linked_pump INTEGER)")
		doCommand(
			"CREATE TABLE IF NOT EXISTS plants (id INTEGER PRIMARY KEY, name TEXT, min_time_aim INTEGER, max_time_aim INTEGER, min_humidity INTEGER, max_humidity INTEGER)")
		doCommand("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)")
		doCommand(
			"CREATE TABLE IF NOT EXISTS plant_managment (user_id INTEGER, plant_id INTEGER, success_setup INTEGER, failed_setup INTEGER)")
		# Create 3 users with names "Alice", "Bob" and "Charlie"
		doCommand("INSERT INTO users (username) VALUES ('Alice')")
		doCommand("INSERT INTO users (username) VALUES ('Bob')")
		doCommand("INSERT INTO users (username) VALUES ('Charlie')")
		# Create 5 plants with names "Tomato", "Potato", "Cactus", "Rose" and "Sunflower"
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Tomato', 6, 8, 30, 40)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Potato', 8, 10, 25, 35)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Cactus', 48, 72, 10, 20)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Rose', 8, 12, 40, 50)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Sunflower', 12, 16, 20, 30)")
		# Create 4 empty fields
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 0)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 1)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 2)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 3)")
		# Create a plant managment for each pair of user / plant
		for i in range(3):
			for j in range(5):
				doCommand("INSERT INTO plant_managment(user_id, plant_id, success_setup, failed_setup) VALUES ({i}, {j}, 0, 0)")
		conn.commit()


class Program(Enum):
	HOUR = 1
	HUMIDITY = 2


class Plant:
	def __init__(self, plant_id: int, name: str, min_time_aim: int, max_time_aim: int,
				min_humidity: int, max_humidity: int):
		self.id: int = plant_id
		self.name: str = name
		self.min_time_aim: int = min_time_aim
		self.max_time_aim: int = max_time_aim
		self.min_humidity: int = min_humidity
		self.max_humidity: int = max_humidity

	@classmethod
	def findById(cls, plant_id: int) -> Self:
		values = doCommand(f"SELECT * FROM plants WHERE id = {plant_id}")
		return cls(plant_id, values[0], values[1], values[2], values[3], values[4])

	@classmethod
	def getAllPlants(cls):
		values = doCommand("SELECT * FROM plants")
		return [cls(v[0], v[1], v[2], v[3], v[4], v[5]) for v in values]


class Field:
	def __init__(self, field_id: int, current_plant: int, saved_prog: int, saved_number: Program, linked_pump: int):
		self.id: int = field_id
		self.current_plant: Plant = Plant.findById(current_plant)
		self.saved_prog: Program = saved_prog
		self.saved_number: int = saved_number
		self.linked_pump: int = linked_pump

	@classmethod
	def findById(cls, field_id: int) -> Self:
		values = doCommand(f"SELECT * FROM fields WHERE id = {field_id}")
		return cls(field_id, values[0], values[1], values[2], values[3])

	@classmethod
	def getAllFields(cls) -> List[Self]:
		values = doCommand("SELECT * FROM fields")
		return [cls(v[0], v[1], v[2], v[3], v[4]) for v in values]

	def save(self):
		doCommand(f"UPDATE fields SET current_plant = {self.current_plant.id}, saved_prog = {self.saved_prog.value}, saved_number = {self.saved_number}, linked_pump = {self.linked_pump} WHERE id = {self.id}")


class User:
	def __init__(self, user_id: int, username: str):
		self.id: int = user_id
		self.username: str = username

	@classmethod
	def findById(cls, user_id: int) -> Self:
		values = doCommand(f"SELECT * FROM users WHERE id = {user_id}")
		return cls(user_id, values[0])

	def getPlants(self) -> List[Plant]:
		return [v.plant for v in PlantManagment.findPlantsOfUser(self.id)]


class PlantManagment:
	def __init__(self, user_id: int, plant_id: int, success_setup: int, failed_setup: int):
		self.user: User = User.findById(user_id)
		self.plant: Plant = Plant.findById(plant_id)
		self.success_setup: int = success_setup
		self.failed_setup: int = failed_setup

	@classmethod
	def findByUserAndPlant(cls, user_id: int, plant_id: int) -> Self:
		values = doCommand(f"SELECT * FROM plant_managment WHERE user_id = {user_id} AND plant_id = {plant_id}")
		return cls(user_id, plant_id, values[0], values[1])

	@classmethod
	def findPlantsOfUser(cls, user_id: int) -> List[Self]:
		values = doCommand(f"SELECT * FROM plant_managment WHERE user_id = {user_id}")
		return [cls(user_id, v[0], v[1], v[2]) for v in values]

	def getSetupRatio(self) -> float:
		return 0 if self.getSetupTimes() == 0 else self.success_setup / self.getSetupTimes()

	def getSetupTimes(self) -> int:
		return self.success_setup + self.failed_setup

	def save(self):
		doCommand(f"UPDATE plant_managment SET success_setup = {self.success_setup}, failed_setup = {self.failed_setup} WHERE user_id = {self.user.id} AND plant_id = {self.plant.id}")


init("reload" in sys.argv)
