from ._anvil_designer import Form2_backupTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
import anvil.server

from datetime import datetime
import anvil.tz

class Form2_backup(Form2_backupTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # Any code you write here will run before the form opens.

  def get_ticker(self):
    stock_str = self.text_box_1.text.strip().upper()

    if anvil.server.call('test_ticker', stock_str):
      opt = anvil.server.call("get_opt_dates_oc", stock_str)
      self.drop_down_1.items = opt
      self.rich_text_1.content = ',  '.join(opt)

      self.drop_down_1.selected_value = opt[8]

      self.button_2.enabled = True
    else:
      alert('invalid ticker')
      self.text_box_1.text = 'SPY'

  def button_1_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.get_ticker()

  def text_box_1_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.get_ticker()

  def button_2_click(self, **event_args):
    """This method is called when the button is clicked"""

    call, put = anvil.server.call('get_opt_markdown_oc', self.text_box_1.text.strip().upper(), self.drop_down_1.selected_value)
    self.rich_text_3.content = call
    self.rich_text_4.content = put

    self.button_3.enabled = True

  def button_3_click(self, **event_args):
    """This method is called when the button is clicked"""
    now_browser = datetime.now(anvil.tz.tzlocal())
    
    res = anvil.server.call('ask_google_csv', self.text_box_1.text.strip().upper(), self.drop_down_1.selected_value, False)
    self.rich_text_2.content = res

    app_tables.table_1.add_row(date=now_browser, response=res)

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form1')

  def link_2_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form3')

  def link_3_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form2')
