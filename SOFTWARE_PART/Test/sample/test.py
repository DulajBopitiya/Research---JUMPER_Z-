class Car:
    def __init__(self , name , model) -> None:
        self.name = name
        self.model = model
        
        
    def display(self) -> None:
        print(f"name : {self.name} , model : {self.model}")
        
    

BMW = Car("Volvo" , 2020)

