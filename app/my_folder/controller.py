import viktor as vkt 


class Controller(vkt.Controller):
    label = 'My Folder'
    children = ['MyEntityType']
    show_children_as = 'Table'
