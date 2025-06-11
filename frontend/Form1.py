from ._anvil_designer import Form1Template
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
import anvil.server

from datetime import datetime
import anvil.tz

class Form1(Form1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # material_light, material_dark rally_light, rally_dark, mykonos_light, mykonos_dark, manarola_light， manarola_dark
    # plotly, plotly_white, plotly_dark, presentation, ggplot2, seaborn, simple_white, gridon, xgridoff, ygridoff
    Plot.templates.default = 'plotly_white'

    self.get_ticker()
    # Any code you write here will run before the form opens.

  def get_ticker(self):
    stock_str = self.text_box_1.text.strip().upper()
    
    if anvil.server.call('test_ticker', stock_str):
      # df markdown
      df_markdown = anvil.server.call('get_df_markdown', stock_str)
      self.rich_text_1.content = df_markdown

      # plot
      data, layout = anvil.server.call('get_fig_data', stock_str)
      fig = go.Figure(data=data, layout=layout)
      
      self.plot_1.visible = True
      self.plot_1.figure = fig

      # button_2
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

    self.label_6.text = 'analyzing...'

    # google
    anvil.server.call('start_google', self.text_box_1.text.strip().upper())
    self.timer_1.interval = 0.5

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form2')
    
  def link_2_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form3')

  def link_5_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('Form4')

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    output, complete = anvil.server.call('stream_google_result')
    self.rich_text_2.content = output

    if complete:
      # stop timer
      self.timer_1.interval = 0
      self.label_6.text = 'analysis completed\n try a different stock ticker'

      # save fig to img
      # img = anvil.server.call('fig_to_img', self.plot_1.figure)
      
      # write to db
      now_browser = datetime.now(anvil.tz.tzlocal())
      app_tables.table_1.add_row(date=now_browser, response=output)
