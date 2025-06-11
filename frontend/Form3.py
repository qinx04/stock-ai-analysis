from ._anvil_designer import Form3Template
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
import anvil.server

from datetime import datetime
import anvil.tz

class Form3(Form3Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self.repeating_panel_1.items = app_tables.table_1.search(
      tables.order_by('date', ascending=False)
    )
    self.label_2.text = self.data_grid_1.get_page() + 1
    # Any code you write here will run before the form opens.

  def button_1_click(self, **event_args):
    """This method is called when the button is clicked"""

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form("Form1")

  def button_3_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.data_grid_1.next_page()
    self.label_2.text = self.data_grid_1.get_page() + 1

  def button_2_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.data_grid_1.previous_page()
    self.label_2.text = self.data_grid_1.get_page() + 1

  def button_5_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.data_grid_1.jump_to_first_page()
    self.label_2.text = self.data_grid_1.get_page() + 1

  def button_4_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.data_grid_1.jump_to_last_page()
    self.label_2.text = self.data_grid_1.get_page() + 1
