from ._anvil_designer import Form4Template
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
import anvil.server

from datetime import datetime
import anvil.tz

class Form4(Form4Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    now_browser = datetime.now(anvil.tz.tzlocal())
    
    self.label_2.text = 'today: ' + now_browser.strftime('%Y-%m-%d, %H:%M:%S, %z')
    # Any code you write here will run before the form opens.

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form1')

  def button_1_click(self, **event_args):
    """This method is called when the button is clicked"""
    re1, re2 = anvil.server.call('get_earning')

    self.rich_text_1.content = re1
    self.rich_text_2.content = re2
