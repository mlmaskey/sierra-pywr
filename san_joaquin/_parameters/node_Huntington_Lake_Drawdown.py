from parameters import WaterLPParameter

from utilities.converter import convert

class node_Huntington_Lake_Drawdown(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):

        return 0
        # date1 = datetime(timestep.water_year-1, 11, 10)
        # date2 = datetime(timestep.water_year-1, 11, 30)
        # if date1 <= timestep.date <= date2:
        #     return 0
        # else:
        #     return 0
        
    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_Huntington_Lake_Drawdown.register()
print(" [*] node_Huntington_Lake_Drawdown successfully registered")
