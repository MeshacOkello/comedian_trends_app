from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objs as go
import plotly
import json
from datetime import datetime, timedelta
import logging
import os

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load data with error handling
csv_file = 'trends_data.csv'
if not os.path.exists(csv_file):
    logger.error(f"{csv_file} not found. Creating empty DataFrame.")
    trends_df = pd.DataFrame(columns=['Month', 'Search_Interest'])
else:
    try:
        trends_df = pd.read_csv(csv_file)
        # Convert YYYY-MM to YYYY-MM-DD (first day of the month)
        trends_df['Month'] = pd.to_datetime(trends_df['Month'] + '-01')
        trends_df = trends_df.rename(columns={'Comedian: (United States)': 'Search_Interest'})
        logger.info("Data loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading {csv_file}: {str(e)}")
        trends_df = pd.DataFrame(columns=['Month', 'Search_Interest'])

@app.route('/', methods=['GET', 'POST'])
def index():
    charts = []
    error = None
    start_date = '2019-12-01'
    end_date = '2025-04-01'

    if request.method == 'POST':
        start_date = request.form.get('start_date', start_date)
        end_date = request.form.get('end_date', end_date)

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            error = "Invalid date format. Use YYYY-MM-DD."
            return render_template('index.html', charts=charts, error=error, start_date=start_date, end_date=end_date)

        if start_dt >= end_dt:
            error = "End date must be after start date."
            return render_template('index.html', charts=charts, error=error, start_date=start_date, end_date=end_date)

        if start_dt < datetime(2019, 12, 1) or end_dt > datetime(2025, 4, 1):
            error = "Dates must be between 2019-12-01 and 2025-04-01."
            return render_template('index.html', charts=charts, error=error, start_date=start_date, end_date=end_date)

        filtered_trends = trends_df[
            (trends_df['Month'] >= start_dt) & 
            (trends_df['Month'] <= end_dt)
        ].copy()

        if filtered_trends.empty:
            error = "No data available for the selected date range."
            return render_template('index.html', charts=charts, error=error, start_date=start_date, end_date=end_date)

        filtered_trends['Month'] = filtered_trends['Month'].dt.strftime('%Y-%m-%d')

        # Calculate months between start and end for dynamic tick spacing
        delta = end_dt - start_dt
        months = delta.days / 30.42  # Approximate months
        if months <= 12:
            tick_interval = "M1"  # Every month for <1 year
        elif months <= 24:
            tick_interval = "M3"  # Every 3 months for 1-2 years
        else:
            tick_interval = "M6"  # Every 6 months for >2 years

        # Chart 1: Smooth Line Chart (Raw Search Interest)
        fig1 = go.Figure()
        fig1.add_trace(
            go.Scatter(
                x=filtered_trends['Month'],
                y=filtered_trends['Search_Interest'],
                name='Search Interest',
                line=dict(color='#3B82F6', width=2, shape='spline'),
                mode='lines+markers'
            )
        )
        fig1.update_xaxes(
            dtick=tick_interval,
            tickformat="%Y-%m",
            title='Date'
        )
        max_interest = filtered_trends['Search_Interest'].max()
        y_range = max(max_interest + 10, 20)
        fig1.update_yaxes(
            dtick=10,  # Multiples of 10
            range=[0, y_range],
            title='Search Interest'
        )
        fig1.update_layout(
            title='Search Interest Over Time',
            height=500,  # Larger chart
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=60, b=40)
        )
        charts.append(json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder))

        # Chart 2: Smooth Line Chart (3-Month Rolling Average)
        filtered_trends['Rolling_Avg'] = filtered_trends['Search_Interest'].rolling(window=3, min_periods=1).mean()
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=filtered_trends['Month'],
                y=filtered_trends['Rolling_Avg'],
                name='3-Month Rolling Average',
                line=dict(color='#10B981', width=2, shape='spline'),
                mode='lines+markers'
            )
        )
        fig2.update_xaxes(
            dtick=tick_interval,
            tickformat="%Y-%m",
            title='Date'
        )
        max_rolling = filtered_trends['Rolling_Avg'].max()
        y_range = max(max_rolling + 10, 20)
        fig2.update_yaxes(
            dtick=10,  # Multiples of 10
            range=[0, y_range],
            title='Search Interest (Rolling Avg)'
        )
        fig2.update_layout(
            title='3-Month Rolling Average of Search Interest',
            height=500,  # Larger chart
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=60, b=40)
        )
        charts.append(json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder))

    return render_template('index.html', charts=charts, error=error, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    app.run(debug=True)