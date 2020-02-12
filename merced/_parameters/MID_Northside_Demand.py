from parameters import CustomParameter

from utilities.converter import convert


class MID_Northside_Demand(CustomParameter):
    """"""

    reductions = [0, 0]

    def _value(self, timestep, scenario_index):

        type_value = self.model.tables['WYT for IFR Below Exchequer'][timestep.year]
        ts = "{}/{}/1900".format(timestep.month, timestep.day)

        if type_value == 1:
            year_type = "Critical"
        elif type_value == 2:
            year_type = "Dry"
        elif type_value == 3:
            year_type = "Below"
        elif type_value == 4:
            year_type = "Above"
        else:
            year_type = "Wet"

        demand_cms = self.model.tables["MID Northside Diversions"].at[ts, year_type] / 35.31

        idx = scenario_index.indices[1]
        if timestep.month == 1 and timestep.day == 1:
            if idx == 1:
                ifr_param = self.model.parameters["IFR at Shaffer Bridge/Min Requirement"]
                reduction = ifr_param.swrcb_levels[scenario_index.indices[0]]
                self.reductions[1] = reduction

        demand_cms *= (1 - self.reductions[idx])
        return demand_cms

    def value(self, timestep, scenario_index):
        try:
            return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1,
                           scale_out=1000000.0)
        except Exception as err:
            print('\nERROR for parameter {}'.format(self.name))
            print('File where error occurred: {}'.format(__file__))
            print(err)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


MID_Northside_Demand.register()
print(" [*] MID_Northside_Demand successfully registered")
