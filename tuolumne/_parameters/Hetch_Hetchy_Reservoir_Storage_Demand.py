from parameters import WaterLPParameter

from utilities.converter import convert

class Hetch_Hetchy_Reservoir_Storage_Demand(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        kwargs = dict(timestep=timestep, scenario_index=scenario_index)
        return {14: 0.0, 39: 1.0, 40: 0.0}.get(period, 0)*(self.GET("node/92016/None", **kwargs) - self.GET("node/92016/65", **kwargs))+self.GET("node/92016/65", **kwargs)
        
    def value(self, timestep, scenario_index):
        try:
            return self._value(timestep, scenario_index)
        except Exception as err:
            print('ERROR for parameter {}'.format(self.name))
            print('File where error occurred: {}'.format(__file__))
            print(err)
            raise

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
Hetch_Hetchy_Reservoir_Storage_Demand.register()
print(" [*] Hetch_Hetchy_Reservoir_Storage_Demand successfully registered")