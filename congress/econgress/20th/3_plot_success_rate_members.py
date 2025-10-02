#!/usr/bin/env python
import plotly.graph_objects as go
import statsmodels.stats.proportion as smp
import pandas as pd


def read_data(house):
    df = pd.read_csv(f'{house}_bills_extended.csv')
    return df
    
def compute_stats(df):
    # Compute success rate per member
    member_stats = df.groupby(
        ['member_name', 'member_id', 'representation', 'member_profile_url']
    ).agg(
        total_bills=('bill_code', 'count'),
        passed_bills=('bill_status', lambda x: (x == 'Passed').sum()),
        theme_focus=('member_theme_focus', 'first')
    ).reset_index()
    
    # Success rate
    member_stats['success_rate'] = member_stats['passed_bills'] / member_stats['total_bills']
    
    # Wilson confidence interval
    ci_low, ci_upp = smp.proportion_confint(
        member_stats['passed_bills'],
        member_stats['total_bills'],
        method='wilson'
    )
    member_stats['ci_low'] = ci_low
    member_stats['ci_upp'] = ci_upp
    return member_stats

def build_plot(member_stats, min_bills=[1, 3, 5, 10, 50, 100], save_html=True):
    # min_bills for dropdown
    
    fig = go.Figure()
    
    for i, t in enumerate(min_bills):
        subset = member_stats[member_stats['total_bills'] >= t].sort_values(by="success_rate")
    
        fig.add_trace(go.Bar(
            x=subset['member_name'],
            y=subset['success_rate'],
            error_y=dict(
                type='data',
                array=subset['ci_upp'] - subset['success_rate'],
                arrayminus=subset['success_rate'] - subset['ci_low']
            ),
            text=subset['success_rate'].map("{:.1%}".format),
            textposition='outside',
            marker_color='skyblue',
            visible=(i == 0),
            customdata=subset[['member_profile_url', 'passed_bills', 'total_bills',
                               'theme_focus', 'representation', 'ci_low', 'ci_upp']].values,
            hovertemplate=(
                '<b>%{x}</b><br>'
                'Success Rate: %{y:.1%}<br>'
                '95% CI: %{customdata[5]:.1%} – %{customdata[6]:.1%}<br>'
                'Passed Bills: %{customdata[1]}<br>'
                'Total Bills: %{customdata[2]}<br>'
                'Theme Focus: %{customdata[3]}<br>'
                'Representation: %{customdata[4]}<extra></extra>'
            )
        ))
    
    # Dropdown buttons inside plot (upper-left)
    buttons = []
    for i, t in enumerate(min_bills):
        visible = [False] * len(min_bills)
        visible[i] = True
        buttons.append(dict(
            label=f"Min {t} bills",
            method="update",
            args=[{"visible": visible},
                  {"title": f"Success Rate of Members (min {t} bills)"}]
        ))
    
    fig.update_layout(
        title=dict(
            text="Success Rate of Members of Congress",
            x=0.5,
            xanchor="center",
            font=dict(size=18)
        ),
        xaxis=dict(
            title=dict(
                text="Member",
                font=dict(size=12)
            ),
            tickangle=-45,
            tickfont=dict(size=10),
            automargin=True
        ),
        yaxis=dict(
            title=dict(
                text="Success Rate (Proportion of Bills Passed)",
                font=dict(size=12)
            ),
            tickformat=".0%"
        ),
        updatemenus=[dict(
            active=3,
            buttons=buttons,
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor="white",
            bordercolor="black"
        )],
        margin=dict(t=80, b=140, l=60, r=20)
    )
    
    fig.add_annotation(
        x=0.5,  # paper coordinates
        y=0.99,
        xref='paper',
        yref='paper',
        text="ℹ️",
        showarrow=False,
        font=dict(size=24, color="blue"),
        hovertext=(
            "Bars show the proportion of a member's bills that were passed.<br>"
            "Error bars indicate 95% confidence intervals (Wilson).<br>"
            "Use the dropdown (upper-left) to filter by members with a minimum number of bills.<br>"
            "<b>Tip:</b> Clicking a member’s name opens their profile in a new tab."
        ),
        hoverlabel=dict(bgcolor="white", font_size=12),
        captureevents=True  # ensures it can respond to clicks if needed
    )
    
    if save_html:
        # Export HTML with clickable bars
        html_file = "success_rate_members.html"
        fig.write_html(html_file, include_plotlyjs='cdn', full_html=True)
        
        with open(html_file, "a") as f:
            f.write("""
        <script>
        var plot = document.getElementsByClassName('plotly-graph-div')[0];
        
        // Clicking a bar opens profile link
        plot.on('plotly_click', function(data){
            var url = data.points[0].customdata[0];
            if(url){
                window.open(url, '_blank');
            }
        });
        </script>
        """)
        
        print("Saved: ", html_file)


if __name__=="__main__":
    house = "house-members"
    df = read_data(house)
    member_stats = compute_stats(df)
    _ = build_plot(member_stats, 
                   min_bills=[1, 3, 5, 10, 50, 100], 
                   save_html=True)