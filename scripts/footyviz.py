from matplotlib import pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.pyplot import arrow
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as path_effects
import numpy as np
import math 
from scipy.spatial import Voronoi
from shapely.geometry import Polygon
import matplotlib.animation as animation
import PitchControl_lastrow as pc

X_SIZE = 105
Y_SIZE = 68

BOX_HEIGHT = (16.5*2 + 7.32)/Y_SIZE*100
BOX_WIDTH = 16.5/X_SIZE*100

GOAL = 7.32/Y_SIZE*100

GOAL_AREA_HEIGHT = 5.4864*2/Y_SIZE*100 + GOAL
GOAL_AREA_WIDTH = 5.4864/X_SIZE*100

SCALERS = np.array([X_SIZE/100, Y_SIZE/100])
pitch_polygon = Polygon(((0,0), (0,100), (100,100), (100,0)))

def draw_pitch(dpi=100, pitch_color='#a8bc95'):
    """Sets up field
    Returns matplotlib fig and axes objects.
    """
    fig = plt.figure(figsize=(12.8, 7.2), dpi=dpi)
    fig.patch.set_facecolor(pitch_color)

    axes = fig.add_subplot(1, 1, 1)
    axes.set_axis_off()
    axes.set_facecolor(pitch_color)
    axes.xaxis.set_visible(False)
    axes.yaxis.set_visible(False)

    axes.set_xlim(0,100)
    axes.set_ylim(0,100)

    plt.xlim([-13.32, 113.32])
    plt.ylim([-5, 105])

    fig.tight_layout(pad=3)

    draw_patches(axes)

    return fig, axes

def draw_patches(axes):
    """
    Draws basic field shapes on an axes
    """
    #pitch
    axes.add_patch(plt.Rectangle((0, 0), 100, 100,
                       edgecolor="white", facecolor="none"))

    #half-way line
    axes.add_line(plt.Line2D([50, 50], [100, 0],
                    c='w'))

    #penalty areas
    axes.add_patch(plt.Rectangle((100-BOX_WIDTH, (100-BOX_HEIGHT)/2),  BOX_WIDTH, BOX_HEIGHT,
                       ec='w', fc='none'))
    axes.add_patch(plt.Rectangle((0, (100-BOX_HEIGHT)/2),  BOX_WIDTH, BOX_HEIGHT,
                               ec='w', fc='none'))

    #goal areas
    axes.add_patch(plt.Rectangle((100-GOAL_AREA_WIDTH, (100-GOAL_AREA_HEIGHT)/2),  GOAL_AREA_WIDTH, GOAL_AREA_HEIGHT,
                       ec='w', fc='none'))
    axes.add_patch(plt.Rectangle((0, (100-GOAL_AREA_HEIGHT)/2),  GOAL_AREA_WIDTH, GOAL_AREA_HEIGHT,
                               ec='w', fc='none'))

    #goals
    axes.add_patch(plt.Rectangle((100, (100-GOAL)/2),  1, GOAL,
                       ec='w', fc='none'))
    axes.add_patch(plt.Rectangle((0, (100-GOAL)/2),  -1, GOAL,
                               ec='w', fc='none'))


    #halfway circle
    axes.add_patch(Ellipse((50, 50), 2*9.15/X_SIZE*100, 2*9.15/Y_SIZE*100,
                                    ec='w', fc='none'))

    return axes

def draw_frame(df, t, dpi=100, fps=20, add_vector=False,display_num=False, display_time=False, show_players=True,
               highlight_color=None, highlight_player=None, shadow_player=None, text_color='white', flip=False, **anim_args):
    """
    Draws players from time t (in seconds) from a DataFrame df
    """
    fig, ax = draw_pitch(dpi=dpi)

    dfFrame = get_frame(df, t, fps=fps)
 
    if show_players:
        for pid in dfFrame.index:
            if pid==0:
                #se for bola
                try:
                    z = dfFrame.loc[pid]['z']
                except:
                    z = 0
                size = 1.2+z
                lw = 0.9
                color='black'
                edge='white'
                zorder = 100
            else:
                #se for jogador
                size = 3
                lw = 2
                edge = dfFrame.loc[pid]['edgecolor']

                if pid == highlight_player:
                    color = highlight_color
                else:
                    color = dfFrame.loc[pid]['bgcolor']
                if dfFrame.loc[pid]['team']=='attack':
                    zorder = 21
                else:
                    zorder = 20

            ax.add_artist(Ellipse((dfFrame.loc[pid]['x'],
                                dfFrame.loc[pid]['y']),
                                size/X_SIZE*100, size/Y_SIZE*100,
                                edgecolor=edge,
                                linewidth=lw,
                                facecolor=color,
                                alpha=0.8,
                                zorder=zorder))
            
            if add_vector:
                
                arrow_length = math.sqrt((dfFrame.loc[pid]['dx']**2 + dfFrame.loc[pid]['dy']**2))*20
                color_arrow = 'white' if pid == 0 else color
                plt.arrow(x=dfFrame.loc[pid]['x'],
                         y=dfFrame.loc[pid]['y'],
                         dx=dfFrame.loc[pid]['dx']*20,
                         dy=dfFrame.loc[pid]['dy']*20,
                         length_includes_head=True,
                         color = color_arrow,
                         edgecolor=edge,
                         head_width=1,
                         head_length=arrow_length/4.)

            try:
                s = str(int(dfFrame.loc[pid]['player_num']))
            except ValueError:
                s = ''
            text = plt.text(dfFrame.loc[pid]['x'],dfFrame.loc[pid]['y'],s,
                            horizontalalignment='center', verticalalignment='center',
                            fontsize=8, color=text_color, zorder=22, alpha=0.8)

            text.set_path_effects([path_effects.Stroke(linewidth=1, foreground=text_color, alpha=0.8),
                                path_effects.Normal()])
            
    return fig, ax, dfFrame

def add_voronoi_to_fig(fig, ax, dfFrame):
    polygons = {}
    vor, dfVor = calculate_voronoi(dfFrame)
    for index, region in enumerate(vor.regions):
        if not -1 in region:
            if len(region)>0:
                try:
                    pl = dfVor[dfVor['region']==index]
                    polygon = Polygon([vor.vertices[i] for i in region]/SCALERS).intersection(pitch_polygon)
                    polygons[pl.index[0]] = polygon
                    color = pl['bgcolor'].values[0]
                    x, y = polygon.exterior.xy
                    plt.fill(x, y, c=color, alpha=0.30)
                except IndexError:
                    pass
                except AttributeError:
                    pass

    plt.scatter(dfVor['x'], dfVor['y'], c=dfVor['bgcolor'], alpha=0.2)

    return fig, ax, dfFrame

def calculate_voronoi(dfFrame):
    dfTemp = dfFrame.copy().drop(0, errors='ignore')

    values = np.vstack((dfTemp[['x', 'y']].values*SCALERS,
                        [-1000,-1000],
                        [+1000,+1000],
                        [+1000,-1000],
                        [-1000,+1000]
                       ))

    vor = Voronoi(values)

    dfTemp['region'] = vor.point_region[:-4]

    return vor, dfTemp

def get_frame(df, t, fps=20):
    dfFrame = df.loc[int(t*fps)].set_index('player')
    dfFrame.player_num = dfFrame.player_num.fillna('')
    return dfFrame

### VISUALISATION FOR PITCH CONTROL
    
def plot_pitch( field_dimen = (106.0,68.0), field_color ='green', linewidth=2, markersize=20):
    """ plot_pitch
    
    Plots a soccer pitch. All distance units converted to meters.
    
    Parameters
    -----------
        field_dimen: (length, width) of field in meters. Default is (106,68)
        field_color: color of field. options are {'green','white'}
        linewidth  : width of lines. default = 2
        markersize : size of markers (e.g. penalty spot, centre spot, posts). default = 20
        
    Returrns
    -----------
       fig,ax : figure and aixs objects (so that other data can be plotted onto the pitch)

    """
    fig,ax = plt.subplots(figsize=(12,8)) # create a figure 
    # decide what color we want the field to be. Default is green, but can also choose white
    if field_color=='green':
        ax.set_facecolor('mediumseagreen')
        lc = 'whitesmoke' # line color
        pc = 'w' # 'spot' colors
    elif field_color=='white':
        lc = 'k'
        pc = 'k'
    # ALL DIMENSIONS IN m
    border_dimen = (3,3) # include a border arround of the field of width 3m
    meters_per_yard = 0.9144 # unit conversion from yards to meters
    half_pitch_length = field_dimen[0]/2. # length of half pitch
    half_pitch_width = field_dimen[1]/2. # width of half pitch
    signs = [-1,1] 
    # Soccer field dimensions typically defined in yards, so we need to convert to meters
    goal_line_width = 8*meters_per_yard
    box_width = 20*meters_per_yard
    box_length = 6*meters_per_yard
    area_width = 44*meters_per_yard
    area_length = 18*meters_per_yard
    penalty_spot = 12*meters_per_yard
    corner_radius = 1*meters_per_yard
    D_length = 8*meters_per_yard
    D_radius = 10*meters_per_yard
    D_pos = 12*meters_per_yard
    centre_circle_radius = 10*meters_per_yard
    # plot half way line # center circle
    ax.plot([0,0],[-half_pitch_width,half_pitch_width],lc,linewidth=linewidth)
    ax.scatter(0.0,0.0,marker='o',facecolor=lc,linewidth=0,s=markersize)
    y = np.linspace(-1,1,50)*centre_circle_radius
    x = np.sqrt(centre_circle_radius**2-y**2)
    ax.plot(x,y,lc,linewidth=linewidth)
    ax.plot(-x,y,lc,linewidth=linewidth)
    for s in signs: # plots each line seperately
        # plot pitch boundary
        ax.plot([-half_pitch_length,half_pitch_length],[s*half_pitch_width,s*half_pitch_width],lc,linewidth=linewidth)
        ax.plot([s*half_pitch_length,s*half_pitch_length],[-half_pitch_width,half_pitch_width],lc,linewidth=linewidth)
        # goal posts & line
        ax.plot( [s*half_pitch_length,s*half_pitch_length],[-goal_line_width/2.,goal_line_width/2.],pc+'s',markersize=6*markersize/20.,linewidth=linewidth)
        # 6 yard box
        ax.plot([s*half_pitch_length,s*half_pitch_length-s*box_length],[box_width/2.,box_width/2.],lc,linewidth=linewidth)
        ax.plot([s*half_pitch_length,s*half_pitch_length-s*box_length],[-box_width/2.,-box_width/2.],lc,linewidth=linewidth)
        ax.plot([s*half_pitch_length-s*box_length,s*half_pitch_length-s*box_length],[-box_width/2.,box_width/2.],lc,linewidth=linewidth)
        # penalty area
        ax.plot([s*half_pitch_length,s*half_pitch_length-s*area_length],[area_width/2.,area_width/2.],lc,linewidth=linewidth)
        ax.plot([s*half_pitch_length,s*half_pitch_length-s*area_length],[-area_width/2.,-area_width/2.],lc,linewidth=linewidth)
        ax.plot([s*half_pitch_length-s*area_length,s*half_pitch_length-s*area_length],[-area_width/2.,area_width/2.],lc,linewidth=linewidth)
        # penalty spot
        ax.scatter(s*half_pitch_length-s*penalty_spot,0.0,marker='o',facecolor=lc,linewidth=0,s=markersize)
        # corner flags
        y = np.linspace(0,1,50)*corner_radius
        x = np.sqrt(corner_radius**2-y**2)
        ax.plot(s*half_pitch_length-s*x,-half_pitch_width+y,lc,linewidth=linewidth)
        ax.plot(s*half_pitch_length-s*x,half_pitch_width-y,lc,linewidth=linewidth)
        # draw the D
        y = np.linspace(-1,1,50)*D_length # D_length is the chord of the circle that defines the D
        x = np.sqrt(D_radius**2-y**2)+D_pos
        ax.plot(s*half_pitch_length-s*x,y,lc,linewidth=linewidth)
        
    # remove axis labels and ticks
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_xticks([])
    ax.set_yticks([])
    # set axis limits
    xmax = field_dimen[0]/2. + border_dimen[0]
    ymax = field_dimen[1]/2. + border_dimen[1]
    ax.set_xlim([-xmax,xmax])
    ax.set_ylim([-ymax,ymax])
    ax.set_axisbelow(True)
    return fig,ax

def plot_frame(attackteam, defenseteam, figax=None, team_colors=('r','b'), field_dimen = (106.0,68.0), include_player_velocities=False, PlayerMarkerSize=10, PlayerAlpha=0.7):
    """ plot_frame(attackteam, defenseteam)
    
    Plots a frame of last Row tracking data (player positions and the ball) on a football pitch. All distances should be in meters.
    
    Parameters
    -----------
        attackteam: row (i.e. instant) of the home team tracking data frame
        defenseteam: row of the away team tracking data frame
        fig,ax: Can be used to pass in the (fig,ax) objects of a previously generated pitch. Set to (fig,ax) to use an existing figure, or None (the default) to generate a new pitch plot, 
        team_colors: Tuple containing the team colors of the home & away team. Default is 'r' (red, home team) and 'b' (blue away team)
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
        include_player_velocities: Boolean variable that determines whether player velocities are also plotted (as quivers). Default is False
        PlayerMarkerSize: size of the individual player marlers. Default is 10
        PlayerAlpha: alpha (transparency) of player markers. Defaault is 0.7
        annotate: Boolean variable that determines with player jersey numbers are added to the plot (default is False)
        
    Returrns
    -----------
       fig,ax : figure and axis objects (so that other data can be plotted onto the pitch)

    """
    if figax is None: # create new pitch 
        fig,ax = plot_pitch( field_dimen = field_dimen )
    else: # overlay on a previously generated pitch
        fig,ax = figax # unpack tuple
    
    # plot home & away teams in order
    for team,color in zip( [attackteam,defenseteam], team_colors) :
        x_pos = np.array(team['x_m'],dtype=float) # column header for player x positions
        y_pos = np.array(team['y_m'],dtype=float) # column header for player y positions
        ax.plot( x_pos, y_pos, color+'o', MarkerSize=PlayerMarkerSize, alpha=PlayerAlpha ) # plot player positions
        if include_player_velocities:
            vx_val = np.array(team['vx_m'],dtype=float) # column header for player x positions
            vy_val = np.array(team['vy_m'],dtype=float) # column header for player y positions
            ax.quiver(x_pos, y_pos, vx_val, vy_val, color=color, scale_units='inches', scale=10.,width=0.0025,headlength=4,headwidth=4,alpha=PlayerAlpha)
    # plot ball
    ax.plot(list(attackteam['ball_x_m'])[0], list(attackteam['ball_y_m'])[0], 'ko', MarkerSize=6, alpha=1.0, LineWidth=0)
    return fig,ax


def plot_pitchcontrol_for_frame(frame, tracking_attack, tracking_defense, PPCF, xgrid, ygrid, alpha = 0.7, include_player_velocities=True, field_dimen = (106.0,68)):
    """ plot_pitchcontrol_for_frame(frame, tracking_home, tracking_away, PPCF, xgrid, ygrid)
    
    Plots the pitch control surface for a given frame. Player and ball positions are overlaid.
    
    Parameters
    -----------
        frame : number relative to the frame on the given play
        tracking_home: (entire) tracking DataFrame for the Home team
        tracking_away: (entire) tracking DataFrame for the Away team
        PPCF: Pitch control surface (dimen (n_grid_cells_x,n_grid_cells_y) ) containing pitch control probability for the attcking team (as returned by the generate_pitch_control_for_event in Metrica_PitchControl)
        xgrid: Positions of the pixels in the x-direction (field length) as returned by the generate_pitch_control_for_event in Metrica_PitchControl
        ygrid: Positions of the pixels in the y-direction (field width) as returned by the generate_pitch_control_for_event in Metrica_PitchControl
        alpha: alpha (transparency) of player markers. Default is 0.7
        include_player_velocities: Boolean variable that determines whether player velocities are also plotted (as quivers). Default is False
        annotate: Boolean variable that determines with player jersey numbers are added to the plot (default is False)
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
        
    Returrns
    -----------
       fig,ax : figure and aixs objects (so that other data can be plotted onto the pitch)

    """    
    
    # plot frame and event
    fig,ax = plot_pitch(field_color='white', field_dimen = field_dimen)
    plot_frame(tracking_attack[tracking_attack['frame']==frame], tracking_defense[tracking_defense['frame']==frame], figax=(fig,ax), PlayerAlpha=alpha, include_player_velocities=include_player_velocities)

    # plot pitch control surface
    cmap = 'bwr'
    ax.imshow(np.flipud(PPCF), extent=(np.amin(xgrid), np.amax(xgrid), np.amin(ygrid), np.amax(ygrid)),interpolation='hanning',vmin=0.0,vmax=1.0,cmap=cmap,alpha=0.5)
    
    return fig,ax