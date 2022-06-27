class Student:
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"
    
    @name.setter
    def name(self, name):
        print("Setter for the name")
        self.first_name, self.last_name = name.split()



student = Student("John", "Smith")
print(student.name)
# print("Student Name:", student.name)
# student.name = "Johnny Smith"
# print("After setting:", student.name)