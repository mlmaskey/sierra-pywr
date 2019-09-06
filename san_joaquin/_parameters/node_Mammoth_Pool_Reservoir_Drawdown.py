from parameters import WaterLPParameter

from utilities.converter import convert

class node_Mammoth_Pool_Reservoir_Drawdown(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):

        return 0
        # date1 = datetime(timestep.water_year-1, 12, 1)
        # date2 = datetime(timestep.water_year, 3, 22)
        # if date1 <= timestep.date <= date2:
        #     return 0
        # else:
        #     return 0
        
    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_Mammoth_Pool_Reservoir_Drawdown.register()
print(" [*] node_Mammoth_Pool_Reservoir_Drawdown successfully registered")
