from parameters import WaterLPParameter

from utilities.converter import convert

class node_Redinger_Lake_Observed_Storage(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        path="Gages/Reservoirs/DailyReservoirGauges.csv"
        return self.read_csv(path)["Redinger Lake"][timestep.datetime]
        
    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_Redinger_Lake_Observed_Storage.register()
print(" [*] node_Redinger_Lake_Observed_Storage successfully registered")
