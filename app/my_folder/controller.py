import viktor as vkt 


class ThrustRestraintController(vkt.Controller):
    label = 'Thrust Restraint'
    children = ['ThrustBlock', "AnchorBlock"] #'ThrustRestrainedPipe',
    show_children_as = 'Table'