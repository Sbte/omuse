from __future__ import print_function
# -*- coding: utf-8 -*-
# %run py_eddy_tracker_classes.py

"""
===========================================================================
This file is part of py-eddy-tracker.

    py-eddy-tracker is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    py-eddy-tracker is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with py-eddy-tracker.  If not, see <http://www.gnu.org/licenses/>.

Copyright (c) 2014-2015 by Evan Mason
Email: emason@imedea.uib-csic.es
===========================================================================

py_eddy_tracker_classes.py

Version 2.0.6
===========================================================================


"""
# External modules
#import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset
import time
import matplotlib.dates as dt
import matplotlib.path as path
import matplotlib.patches as patch
import mpl_toolkits.basemap.pyproj as pyproj
from . import make_eddy_tracker_list_obj as eddy_tracker
from .py_eddy_tracker_property_classes import Amplitude, EddyProperty, interpolate
#from haversine import haversine # needs compiling with f2py
from . import haversine_distmat_python as haversine 
import scipy.sparse as sparse


def datestr2datetime(datestr):
    """
    Take strings with format YYYYMMDD and convert to datetime instance
    """
    message = "'datestr' must have length 8"
    assert len(datestr) == 8, message
    message = "first character of 'datestr' should be '1' or '2'"
    assert datestr[0] in ('1', '2'), message
    return dt.datetime.datetime(np.int(datestr[:4]),
                                np.int(datestr[4:6]),
                                np.int(datestr[6:]))


def gaussian_resolution(res, zwl, mwl):
    """
    Get parameters for ndimage.gaussian_filter
    See http://stackoverflow.com/questions/14531072/how-to-count-bugs-in-an-image
    Input: res : grid resolution in degrees
           zwl : zonal distance in degrees
           mwl : meridional distance in degrees
    """
    zres = zwl.copy()
    mres = mwl.copy()
    zres *= 0.125
    mres *= 0.125
    zres /= res
    mres /= res
    return zres, mres


def do_basemap(M, ax):
    """
    Convenience method for Basemap functions
    """
    londiff = np.array([M.lonmin, M.lonmax]).ptp()
    latdiff = np.array([M.latmin, M.latmax]).ptp()
    if (londiff > 60) or (latdiff > 60):
        stride = 12.
    elif (londiff > 40) or (latdiff > 40):
        stride = 8.
    elif (londiff > 30) or (latdiff > 30):
        stride = 5.
    elif (londiff > 15) or (latdiff > 15):
        stride = 3.
    else:
        stride = 2
    M.drawparallels(np.arange(-90, 90 + stride, stride),
                    labels=[1, 0, 0, 0], linewidth=0.25, size=8, ax=ax)
    M.drawmeridians(np.arange(-360, 360 + stride, stride),
                    labels=[0, 0, 0, 1], linewidth=0.25, size=8, ax=ax)
    M.fillcontinents('k', ax=ax, zorder=20)
    M.drawcoastlines(linewidth=0.5, ax=ax, zorder=20)
    return


def anim_figure(A_eddy, C_eddy, Mx, My, MMx, MMy, cmap, rtime, DIAGNOSTIC_TYPE,
                savedir, tit, ax, ax_cbar, qparam=None, qparameter=None,
                xi=None, xicopy=None, track_length=0, plot_all=False):
    """
    """
    def plot_tracks(Eddy, track_length, rtime, col, ax, plot_all):
        if plot_all:
            eddylist = list(range(len(Eddy.tracklist)))
        else:
            eddylist = Eddy.get_active_tracks(rtime)
        for i in eddylist:
            # filter for longer tracks
            if len(Eddy.tracklist[i].lon) > track_length:
                aex, aey = Eddy.M(np.asarray(Eddy.tracklist[i].lon),
                                  np.asarray(Eddy.tracklist[i].lat))
                #if (np.any(np.isclose(Eddy.tracklist[i].lon, -25.1014658767)) and
                    #np.any(np.isclose(Eddy.tracklist[i].lat, 67.7787233626))):
                    #print Eddy.tracklist[i].lon
                    #plt.figure(638)
                    #plt.plot(aex, aey)
                    #plt.axis('image')
                    #plt.show()
                M.plot(aex, aey, col, lw=0.5, ax=ax, zorder=6)
                M.scatter(aex[-1], aey[-1], s=7, c=col, edgecolor='w',
                          ax=ax, zorder=5)
        return

    M = A_eddy.M

    if 'Q' in DIAGNOSTIC_TYPE:
        pcm = M.pcolormesh(MMx, MMy, xicopy, cmap=cmap, ax=ax,
                           interpolation='none')
        M.contour(Mx, My, xi, [0.], ax=ax, colors='k', linewidths=0.5)
        M.contour(Mx, My, qparam, qparameter, ax=ax, colors='g',
                  linewidths=0.25)
        pcm.set_clim(-.5, .5)
        M.contour(Mx, My, qparam, [qparameter[0]], ax=ax, colors='m',
                  linewidths=0.25)

    elif 'SLA' in DIAGNOSTIC_TYPE:
        pcm = M.pcolormesh(MMx, MMy, A_eddy.slacopy, cmap=cmap, ax=ax)
        M.contour(Mx, My, A_eddy.slacopy, [0.], ax=ax, colors='k',
                  linewidths=0.5)
        M.contour(Mx, My, A_eddy.slacopy, A_eddy.CONTOUR_PARAMETER, ax=ax,
                  colors='g',
                  linestyles='solid', linewidths=0.15)
        pcm.set_clim(-20., 20.)
    plot_tracks(A_eddy, track_length, rtime, 'r', ax, plot_all)
    plot_tracks(C_eddy, track_length, rtime, 'b', ax, plot_all)

    do_basemap(M, ax)

    ax.set_title(tit)
    plt.colorbar(pcm, cax=ax_cbar, orientation='horizontal')
    plt.savefig(savedir + 'eddy_track_%s.png' % tit.replace(' ', '_'),
                dpi=150, bbox_inches='tight')
    #plt.show()
    ax.cla()
    ax_cbar.cla()
    return


def get_cax(subplot, dx=0, width=.015, position='r'):
    """
    Return axes for colorbar same size as subplot
      subplot - subplot object
      dx - distance from subplot to colorbar
      width - width of colorbar
      position - 'r' - right (default)
               - 'b' - bottom
    """
    assert position in ('b', 'r'), 'position must be "r" or "b"'
    cax = subplot.get_position().get_points()
    if position in 'r' and 'r' in position:
        cax = plt.axes([cax[1][0] + dx, cax[0][1],
                        width, cax[1][1] - cax[0][1]])
    if position in 'b' and 'b' in position:
        cax = plt.axes([cax[0][0], cax[0][1] - 2 * dx,
                        cax[1][0] - cax[0][0], width])
    return cax


def oceantime2ymd(ocean_time, integer=False):
    """
    Return strings *yea*r, *month*, *day* given ocean_time (seconds)
    If kwarg *integer*==*True* return integers rather than strings.
    """
    if np.isscalar(ocean_time):
        ocean_time = np.array([ocean_time])
    ocean_time /= 86400.
    year = np.floor(ocean_time / 360.)
    month = np.floor((ocean_time - year * 360.) / 30.)
    day = np.floor(ocean_time - year * 360. - month * 30.)
    year = (year.astype(np.int16) + 1)[0]
    month = (month.astype(np.int16) + 1)[0]
    day = (day.astype(np.int16) + 1)[0]
    if not integer:
        year = str(year)
        if len(year) < 2:
            year = year.zfill(2)
        month = str(month)
        if len(month) < 2:
            month = month.zfill(2)
        day = str(day)
        if len(day) < 2:
            day = day.zfill(2)
    return year, month, day


def half_interp(h1, h2):
    """
    Speed up for frequent operations
    """
    h1 = h1.copy()
    h2 = h2.copy()
    h1 += h2
    h1 *= 0.5
    return h1


def quart_interp(h1, h2, h3, h4):
    """
    Speed up for frequent operations
    """
    return ne.evaluate('0.25 * (h1 + h2 + h3 + h4)')


def okubo_weiss(grd):
    """
    Calculate the Okubo-Weiss parameter
    See e.g. http://ifisc.uib.es/oceantech/showOutput.php?idFile=61
    Returns: lambda2 - Okubo-Weiss parameter [s^-2]
             xi      - rel. vorticity [s^-1]
    Adapted from Roms_tools
    """
    def vorticity(u, v, pm, pn):
        """
        Returns vorticity calculated using np.gradient
        """
        def vort(u, v, dx, dy):
            dx = ne.evaluate('1 / dx')
            dy = ne.evaluate('1 / dy')
            uy, ux = np.gradient(grd.u2rho_2d(u), dx, dy)
            vy, vx = np.gradient(grd.v2rho_2d(v), dx, dy)
            xi = ne.evaluate('vx - uy')
            return xi
        return vort(u, v, pm, pn)
    u = grd.rho2u_2d(grd.u)
    v = grd.rho2v_2d(grd.v)
    pm = grd.pm()[grd.jup0:grd.jup1, grd.iup0:grd.iup1]
    pn = grd.pn()[grd.jup0:grd.jup1, grd.iup0:grd.iup1]

    Mp, Lp = pm.shape
    L = ne.evaluate('Lp - 1')
    M = ne.evaluate('Mp - 1')
    Lm = ne.evaluate('L - 1')
    Mm = ne.evaluate('M - 1')
    mn_p = np.zeros((M, L))
    uom = np.zeros((M, Lp))
    von = np.zeros((Mp, L))
    uom = 2. * u / (pm[:, :L] + pm[:, 1:Lp])
    uon = 2. * u / (pn[:, :L] + pn[:, 1:Lp])
    von = 2. * v / (pn[:M] + pn[1:Mp])
    vom = 2. * v / (pm[:M] + pm[1:Mp])
    mn = pm * pn
    mn_p = quart_interp(mn[:M, :L], mn[:M, 1:Lp],
                        mn[1:Mp, 1:Lp], mn[1:Mp, :L])
    # Sigma_T
    ST = mn * psi2rho(von[:, 1:Lp] - von[:, :L] + uom[1:Mp, :] - uom[:M, :])
    # Sigma_N
    SN = np.zeros((Mp, Lp))
    SN[1:-1, 1:-1] = mn[1:-1, 1:-1] * (uon[1:-1, 1:]
                                       - uon[1:-1, :-1]
                                       - vom[1:, 1:-1]
                                       + vom[:-1, 1:-1])
    # Relative vorticity
    xi = vorticity(u, v, pm, pn)
    # Okubo
    lambda2 = SN**2
    lambda2 += ST**2
    lambda2 -= xi**2
    return lambda2, xi


def psi2rho(var_psi):
    # Convert a psi field to rho points
    M, L = var_psi.shape
    Mp = M + 1
    Lp = L + 1
    Mm = M - 1
    Lm = L - 1
    var_rho = np.zeros((Mp, Lp))
    var_rho[1:M, 1:L] = quart_interp(var_psi[:Mm, :Lm], var_psi[:Mm, 1:L],
                                     var_psi[1:M, :Lm], var_psi[1:M, 1:L])
    var_rho[0] = var_rho[1]
    var_rho[M] = var_rho[Mm]
    var_rho[:, 0] = var_rho[:, 1]
    var_rho[:, L] = var_rho[:, Lm]
    return var_rho

def pcol_2dxy(x, y):
    """
    Function to shift x, y for subsequent use with pcolor
    by Jeroen Molemaker UCLA 2008
    """
    Mp, Lp = x.shape
    M = Mp - 1
    L = Lp - 1
    x_pcol = np.zeros((Mp, Lp))
    y_pcol = np.zeros_like(x_pcol)
    x_tmp = half_interp(x[:, :L], x[:, 1:Lp])
    x_pcol[1:Mp, 1:Lp] = half_interp(x_tmp[0:M], x_tmp[1:Mp])
    x_pcol[0] = 2. * x_pcol[1] - x_pcol[2]
    x_pcol[:, 0] = 2. * x_pcol[:, 1] - x_pcol[:, 2]
    y_tmp = half_interp(y[:, :L], y[:, 1:Lp]    )
    y_pcol[1:Mp, 1:Lp] = half_interp(y_tmp[:M], y_tmp[1:Mp])
    y_pcol[0] = 2. * y_pcol[1] - y_pcol[2]
    y_pcol[:, 0] = 2. * y_pcol[:, 1] - y_pcol[:, 2]
    return x_pcol, y_pcol


def fit_circle(xvec, yvec):
    """
    Fit the circle
    Adapted from ETRACK (KCCMC11)
    """
    xvec, yvec = xvec.copy(), yvec.copy()

    if xvec.ndim == 1:
        xvec = xvec[np.newaxis]
    if yvec.ndim == 1:
        yvec = yvec[np.newaxis]
    if xvec.shape[1] != 1:
        xvec = xvec.T
    if yvec.shape[1] != 1:
        yvec = yvec.T

    npts = xvec.size
    xmean = xvec.mean()
    ymean = yvec.mean()
    xsc = xvec - xmean
    ysc = yvec - ymean

    scale = np.sqrt((xsc**2 + ysc**2).max())

    xsc /= scale
    ysc /= scale

    # Form matrix equation and solve it
    #print np.concatenate((2. * xsc, 2. * ysc, np.ones((npts, 1))), axis=1)
    #print xsc**2 + ysc**2
    xyz = np.linalg.lstsq(
        np.concatenate((2. * xsc, 2. * ysc, np.ones((npts, 1))), axis=1),
        xsc**2 + ysc**2)
    #print xyz
    #plt.plot(2. * xsc)
    #exit()
    # Unscale data and get circle variables
    p = np.concatenate((xyz[0][0], xyz[0][1],
                        np.sqrt(xyz[0][2] + xyz[0][0]**2 + xyz[0][1]**2)))
    p *= scale
    p += np.array([xmean, ymean, 0.])

    ccx = p[0]  # center X-position of fitted circle
    ccy = p[1]  # center Y-position of fitted circle
    r = p[2]  # radius of fitted circle
    carea = r**2 * np.pi  # area of fitted circle

    # Shape test
    # Area and centroid of closed contour/polygon
    xvec1 = xvec[:npts-1]
    yvec1 = yvec[1:npts]
    xvec2 = xvec[1:npts]
    yvec2 = yvec[:npts-1]
    tmp = (xvec1 * yvec1) - (xvec2 * yvec2)
    polar = tmp.sum()
    polar *= 0.5
    parea = np.abs(polar)

    # Find distance between circle center and contour points_inside_poly
    dist_poly = np.sqrt((xvec - ccx)**2 + (yvec - ccy)**2)

    sintheta = (yvec - ccy) / dist_poly
    ptmp_y = ccy + (r * sintheta)
    ptmp_x = ccx - (ccx - xvec) * ((ccy - ptmp_y) / (ccy - yvec))

    # Indices of polygon points outside circle
    # p_inon_? : polygon x or y points inside & on the circle
    pout_id = (dist_poly > r).nonzero()

    p_inon_x = xvec  # init
    p_inon_y = yvec  # init
    p_inon_x[pout_id] = ptmp_x[pout_id]
    p_inon_y[pout_id] = ptmp_y[pout_id]

    # Area of closed contour/polygon enclosed by the circle
    tmp = ((p_inon_x[0:npts-1] * p_inon_y[1:npts]) -
           (p_inon_x[1:npts] * p_inon_y[0:npts-1]))

    parea_incirc = np.abs(tmp.sum())
    parea_incirc *= 0.5
    aerr = (1 - parea_incirc / carea) + (parea - parea_incirc) / carea
    aerr *= 100.
    return ccx, ccy, r, aerr


def get_uavg(Eddy, CS, collind, centlon_e, centlat_e, poly_eff,
             grd, eddy_radius_e, save_all_uavg=False):
    """
    Calculate geostrophic speed around successive contours
    Returns the average

    If save_all_uavg == True we want uavg for every contour
    """
    # Unpack indices for convenience
    imin, imax, jmin, jmax = Eddy.imin, Eddy.imax, Eddy.jmin, Eddy.jmax

    points = np.array([grd.lon()[jmin:jmax, imin:imax].ravel(),
                       grd.lat()[jmin:jmax, imin:imax].ravel()]).T

    #print points.shape
    #print Eddy.uspd.ravel().shape

    # First contour is the outer one (effective)
    theseglon, theseglat = (poly_eff.vertices[:, 0].copy(),
                            poly_eff.vertices[:, 1].copy())

    theseglon, theseglat = eddy_tracker.uniform_resample(
        theseglon, theseglat, method='interp1d', extrapolate=True)

    if 'AVISO' in Eddy.PRODUCT:
        if 'RectBivariate' in Eddy.INTERP_METHOD:
            uavg = Eddy.uspd_coeffs.ev(theseglat[1:], theseglon[1:]).mean()

        elif 'griddata' in Eddy.INTERP_METHOD:
            uspd1d = Eddy.uspd[jmin:jmax, imin:imax].ravel()
            uavg = interpolate.griddata(points, uspd1d,
                                        (theseglon[1:], theseglat[1:]), 'linear')
            uavg = uavg[np.isfinite(uavg)].mean()
        else:
            Exception
    
    elif 'ROMS' in Eddy.PRODUCT:
        uavg = Eddy.uspd_coeffs(theseglon[1:], theseglat[1:])
        uavg = uavg[np.isfinite(uavg)].mean()

    elif 'Generic' in Eddy.PRODUCT: #do same as AVISO
        uavg = Eddy.uspd_coeffs.ev(theseglat[1:], theseglon[1:]).mean()

    else:
        Exception

    if save_all_uavg:
        all_uavg = [uavg]
        pixel_min = 1  # iterate until 1 pixel

    else:
        # Iterate until PIXEL_THRESHOLD[0] number of pixels
        pixel_min = Eddy.PIXEL_THRESHOLD[0]

    # Flag as True if contours found within effective contour
    any_inner_contours = False

    citer = np.nditer(CS.cvalues, flags=['c_index'])

    while not citer.finished:
        ## Get contour around centlon_e, centlat_e at level [collind:][iuavg]
        #theindex, poly_i = eddy_tracker.find_nearest_contour(
                        #CS.collections[citer.index], centlon_e, centlat_e)

        Eddy.swirl.set_dist_array_size(citer.index)

        # Leave loop if no contours at level citer.index
        if Eddy.swirl.level_slice is None:
            citer.iternext()
            continue

        Eddy.swirl.set_nearest_contour_index(centlon_e, centlat_e)
        theindex = Eddy.swirl.get_index_nearest_path()

        if theindex is not False:

            poly_i = CS.collections[citer.index].get_paths()[theindex]

            # 1. Ensure polygon_i contains point centlon_e, centlat_e
            if poly_i.contains_point([centlon_e, centlat_e]):

                # 2. Ensure polygon_i is within polygon_e
                if poly_eff.contains_path(poly_i):

                    # 3. Respect size range
                    mask_i_sum = poly_i.contains_points(points).sum()
                    if (mask_i_sum >= pixel_min and
                        mask_i_sum <= Eddy.PIXEL_THRESHOLD[1]):

                        any_inner_contours = True

                        seglon, seglat = (poly_i.vertices[:, 0].copy(),
                                          poly_i.vertices[:, 1].copy())
                        seglon, seglat = eddy_tracker.uniform_resample(
                            seglon, seglat, method='interp1d')

                        # Interpolate uspd to seglon, seglat, then get mean
                        if 'AVISO' in Eddy.PRODUCT:
                            if 'RectBivariate' in Eddy.INTERP_METHOD:
                                uavgseg = Eddy.uspd_coeffs.ev(seglat[1:],
                                                              seglon[1:]).mean()

                            elif 'griddata' in Eddy.INTERP_METHOD:
                                uavgseg = interpolate.griddata(points, uspd1d,
                                        (seglon[1:], seglat[1:]), 'linear')
                                uavgseg = uavgseg[np.isfinite(uavgseg)].mean()
                            else:
                                Exception
                                
                                
                        elif 'ROMS' in Eddy.PRODUCT:
                            uavgseg = Eddy.uspd_coeffs(theseglon[1:], theseglat[1:])
                            uavgseg = uavg[np.isfinite(uavg)].mean()

                        elif 'Generic' in Eddy.PRODUCT: #do same as AVISO
                            uavgseg = Eddy.uspd_coeffs.ev(seglat[1:],
                                                          seglon[1:]).mean()
                        
                        if save_all_uavg:
                            all_uavg.append(uavgseg)

                        if uavgseg >= uavg:
                            uavg = uavgseg.copy()
                            theseglon, theseglat = seglon.copy(), seglat.copy()

                        inner_seglon, inner_seglat = seglon.copy(), seglat.copy()

        citer.iternext()

    if not any_inner_contours:  # set speed based contour parameters
        inner_seglon, inner_seglat = theseglon, theseglat

    if not save_all_uavg:
        return (uavg, theseglon, theseglat,
                inner_seglon, inner_seglat, any_inner_contours)
    else:
        return (uavg, theseglon, theseglat,
                inner_seglon, inner_seglat, any_inner_contours, all_uavg)


def collection_loop(CS, grd, rtime, A_list_obj, C_list_obj,
                    xi=None, CSxi=None, sign_type='None', VERBOSE=False):
    """
    Loop over each collection of contours
    """
    if A_list_obj is not None:
        Eddy = A_list_obj
    if C_list_obj is not None:
        Eddy = C_list_obj

    if 'ROMS' in Eddy.PRODUCT:
        #has_ts = True
        has_ts = False
    elif 'AVISO' in Eddy.PRODUCT:
        has_ts = False
    elif 'Generic' in Eddy.PRODUCT:
        has_ts = False
    else:
        Exception  # unknown PRODUCT

    # Unpack indices for convenience
    istr, iend, jstr, jend = Eddy.i0, Eddy.i1, Eddy.j0, Eddy.j1

    # Set contour coordinates and indices for calculation of
    # speed-based radius
    #swirl = SwirlSpeed(Eddy, CS)

    # Loop over each collection
    for collind, coll in enumerate(CS.collections):

        if VERBOSE:
            message = '------ doing collection %s, contour value %s'
            print(message % (collind, CS.cvalues[collind]))

        # Loop over individual CS contours (i.e., every eddy in field)
        for cont in coll.get_paths():

            contlon_e, contlat_e = cont.vertices[:, 0].copy(), \
                                   cont.vertices[:, 1].copy()

            # Filter for closed contours
            if np.alltrue([contlon_e[0] == contlon_e[-1],
                           contlat_e[0] == contlat_e[-1],
                           contlon_e.ptp(),
                           contlat_e.ptp()]):

                # Instantiate new EddyProperty object
                properties = EddyProperty(TRACK_EXTRA_VARIABLES=
                                          Eddy.TRACK_EXTRA_VARIABLES)

                # Prepare for shape test and get eddy_radius_e
                #cx, cy = Eddy.M(contlon_e, contlat_e)
                
                #proj = pyproj.Proj(proj='aeqd', lat_0=contlat_e.mean(), lon_0=contlon_e.mean())#, width=5.e2, height=5.e2)
                # http://www.geo.hunter.cuny.edu/~jochen/gtech201/lectures/lec6concepts/map%20coordinate%20systems/how%20to%20choose%20a%20projection.htm
                contlon_e_mean = contlon_e.mean()
                proj = pyproj.Proj('+proj=aeqd +lat_0=%s +lon_0=%s'
                                   % (contlat_e.mean(), contlon_e_mean))
                cx, cy = proj(contlon_e, contlat_e)
                #print '--------------', cx.ptp(), cx.min(), cx.max()
                centlon_e, centlat_e, eddy_radius_e, aerr = fit_circle(cx, cy)

                aerr = np.atleast_1d(aerr)

                # Filter for shape: >35% (>55%) is not an eddy for Q (SLA)
                if True: #shape test disabled by Ben
                #if aerr >= 0. and aerr <= Eddy.SHAPE_ERROR[collind]:

                    # Get centroid in lon lat
                    centlon_e, centlat_e = proj(centlon_e, centlat_e, inverse=True)

                    # Proj makes lons < -180 positive, and vice-versa for +180
                    # FIXME (this is a fix for global grid, but it may cause
                    # problems later for, say, Pacific grids ... need to check)
                    if contlon_e_mean < -180.:
                        centlon_e -= 360.
                    if contlon_e_mean >= 180.:
                        centlon_e += 360.
                        
                    # For some reason centlat_e is transformed
                    # by projtran to 'float'...
                    centlon_e, centlat_e = (np.float64(centlon_e),
                                            np.float64(centlat_e))

                    # Get eddy_radius_e (NOTE: if Q, we overwrite
                    # eddy_radius_e defined several lines above)
                    if 'Q' in Eddy.DIAGNOSTIC_TYPE:
                        xilon, xilat = CSxi.find_nearest_contour(
                            centlon_e, centlat_e, pixel=False)[3:5]
                        eddy_radius_e = haversine.distance(centlon_e,
                                                           centlat_e,
                                                           xilon, xilat)
                        if (eddy_radius_e >= Eddy.radmin and
                                eddy_radius_e <= Eddy.radmax):
                            proceed0 = True
                        else:
                            proceed0 = False

                    elif 'SLA' in Eddy.DIAGNOSTIC_TYPE:
                        # If 'SLA' is defined we filter below with pixel count
                        proceed0 = True

                    else:
                        raise Exception
                    if proceed0:

                        # Get indices of centroid
                        centi, centj = eddy_tracker.nearest(
                            centlon_e, centlat_e,
                            grd.lon(), grd.lat(), grd.shape)

                        if 'Q' in Eddy.DIAGNOSTIC_TYPE:

                            if xi[centj, centi] != Eddy.FILLVAL:
                                proceed1 = True
                            else:
                                proceed1 = False

                        elif 'SLA' in Eddy.DIAGNOSTIC_TYPE:

                            if Eddy.sla[centj, centi] != Eddy.FILLVAL:
                                acyc_not_cyc = (Eddy.sla[centj, centi] >=
                                                CS.cvalues[collind])
                                if ('Anticyclonic' in sign_type and
                                        acyc_not_cyc):
                                    proceed1 = True
                                elif ('Cyclonic' in sign_type and not
                                      acyc_not_cyc):
                                    proceed1 = True
                                else:
                                    proceed1 = False  # no eddy
                            else:
                                proceed1 = False
                        else:
                            raise Exception

                        if proceed1:

                            # Set indices to bounding box around eddy
                            Eddy.set_bounds(contlon_e, contlat_e, grd)

                            # Unpack indices for convenience
                            imin, imax, jmin, jmax = (Eddy.imin, Eddy.imax,
                                                      Eddy.jmin, Eddy.jmax)

                            # Set masked points within bounding box around eddy
                            Eddy.set_mask_eff(cont, grd)

                            # sum(mask) between 8 and 1000, CSS11 criterion 2
                            if (Eddy.mask_eff_sum >= Eddy.PIXEL_THRESHOLD[0] and
                                    Eddy.mask_eff_sum <= Eddy.PIXEL_THRESHOLD[1]):

                                Eddy.reshape_mask_eff(grd)

                                # Resample the contour points for a more even
                                # circumferential distribution
                                contlon_e, contlat_e = \
                                    eddy_tracker.uniform_resample(
                                        contlon_e, contlat_e)

                                if 'Q' in Eddy.DIAGNOSTIC_TYPE:
                                    # Note, eddy amplitude == max(abs(vort/f)) within eddy, KCCMC11
                                    #amplitude = np.abs(xi[jmin:jmax,imin:imax].flat[mask_eff]).max()
                                    amplitude = np.abs(xi[jmin:jmax,imin:imax][Eddy.mask_eff]).max()

                                elif 'SLA' in Eddy.DIAGNOSTIC_TYPE:

                                    # Instantiate Amplitude object
                                    amp = Amplitude(contlon_e, contlat_e, Eddy, grd)

                                    if 'Anticyclonic' in sign_type:
                                        reset_centroid = amp.all_pixels_above_h0(
                                                              CS.levels[collind])
                                    elif 'Cyclonic' in sign_type:
                                        reset_centroid = amp.all_pixels_below_h0(
                                                              CS.levels[collind])
                                    else:
                                        Exception

                                    if reset_centroid:
                                        centi = reset_centroid[0]
                                        centj = reset_centroid[1]
                                        centlon_e = grd.lon()[centj, centi]
                                        centlat_e = grd.lat()[centj, centi]

                                    #amp.debug_figure(grd)

                                    if amp.within_amplitude_limits():
                                        properties.amplitude = amp.amplitude

                            if properties.amplitude:

                                # Get sum of eke within Ceff
                                teke = grd.eke[jmin:jmax, imin:imax][Eddy.mask_eff].sum()

                                if 'Q' in Eddy.DIAGNOSTIC_TYPE:
                                    #print 'change to rectbispline'
                                    #uavg = interpolate.griddata(points, Eddy.uspd[jmin:jmax,imin:imax].ravel(),
                                                                #(contlon_e, contlat_e), 'linear')
                                    #uavg = np.nan_to_num(uavg).max()
                                    ##uavg = 0; print 'fix me'
                                    ## Get indices of speed-based centroid
                                    #centi, centj = eddy_tracker.nearest(centlon_s, centlat_s,
                                                                        #grd.lon(), grd.lat(), grd.shape)
                                    pass

                                elif 'SLA' in Eddy.DIAGNOSTIC_TYPE:

                                    args = (Eddy, CS, collind,
                                            centlon_e, centlat_e,
                                            cont, grd, eddy_radius_e)

                                    if not Eddy.TRACK_EXTRA_VARIABLES:
                                        #(uavg, centlon_s, centlat_s,
                                         #eddy_radius_s, contlon_s, contlat_s,
                                         #inner_contlon, inner_contlat) = get_uavg(*args)
                                        (uavg, contlon_s, contlat_s,
                                         inner_contlon, inner_contlat,
                                         any_inner_contours) = get_uavg(*args)
                                    else:
                                        #(uavg, centlon_s, centlat_s,
                                         #eddy_radius_s, contlon_s, contlat_s,
                                         #inner_contlon, inner_contlat,
                                         #uavg_profile) = get_uavg(*args, save_all_uavg=True)
                                        (uavg, contlon_s, contlat_s,
                                         inner_contlon, inner_contlat,
                                         any_inner_contours, uavg_profile) = get_uavg(
                                             *args, save_all_uavg=True)

                                    if any_inner_contours:
                                        # Use azimuth equal projection for radius
                                        inner_contlon_mean = inner_contlon.mean()
                                        proj = pyproj.Proj('+proj=aeqd +lat_0=%s +lon_0=%s'
                                                        % (inner_contlat.mean(),
                                                           inner_contlon_mean))
                                        
                                        # First, get position based on innermost contour
                                        cx, cy = proj(inner_contlon, inner_contlat)
                                        centx_s, centy_s, _, _ = fit_circle(cx, cy)
                                        centlon_s, centlat_s = proj(centx_s, centy_s,
                                                                    inverse=True)
                                        
                                        # Proj makes lons < -180 positive, and vice-versa for +180
                                        # FIXME (this is a fix for global grid, but it may cause
                                        # problems later for, say, Pacific grids ... need to check)
                                        if inner_contlon_mean < -180.:
                                            centlon_s -= 360.
                                        if inner_contlon_mean >= 180.:
                                            centlon_s += 360.
                                    else:
                                        centlon_s, centlat_s = centlon_e, centlat_e

                                    # NOTE This can be instructive, there's some strange
                                    # things sometimes...
                                    #if abs(centlon_s - centlon_e) > 0.25 and not any_inner_contours:
                                        #print any_inner_contours
                                        #print centlon_s - centlon_e
                                        #plt.figure()
                                        #plt.plot(contlon_s, contlat_s, '-+g', lw=2)
                                        #plt.plot(contlon_e, contlat_e, '-or', alpha=.5)
                                        #plt.scatter(centlon_s, centlat_s, s=50, c='g')
                                        #plt.scatter(centlon_e, centlat_e, s=50, c='r')
                                        #plt.axis('image')
                                        #plt.show()
                                    
                                    # Second, get speed-based radius based on
                                    # contour of max uavg
                                    # (perhaps we could make a new proj here based on
                                    #  contlon_s, contlat_s but I'm not sure it's
                                    #  that important ... )
                                    cx, cy = proj(contlon_s, contlat_s)
                                    _, _, eddy_radius_s, _ = fit_circle(cx, cy)

                                # Define T and S if needed
                                #if has_ts:
                                    ## Temperature at centroid
                                    #cent_temp = temp[centj, centi]
                                    ## Salinity at centroid
                                    #cent_salt = salt[centj, centi]

                                properties.eddy_radius_s = eddy_radius_s
                                properties.uavg = uavg
                                properties.eddy_radius_e = eddy_radius_e
                                properties.rtime = rtime
                                properties.teke = teke

                                # Update Q eddy properties
                                if 'Q' in Eddy.DIAGNOSTIC_TYPE:
                                    # We pass eddy_radius_e as a dummy for eddy_radius_s

                                    if has_ts:  # for ocean model
                                        if xi[centj, centi] <= 0.:  # Anticyclone
                                            A_list_obj.update_eddy_properties(centlon_e, centlat_e,
                                                                          eddy_radius_e, eddy_radius_e,
                                                                          amplitude, uavg, teke, rtime,
                                                                          cent_temp=cent_temp,
                                                                          cent_salt=cent_salt)
                                        elif xi[centj, centi] >= 0.:  # Cyclone
                                            C_list_obj.update_eddy_properties(centlon_e, centlat_e,
                                                                          eddy_radius_e, eddy_radius_e,
                                                                          amplitude, uavg, teke, rtime,
                                                                          cent_temp=cent_temp,
                                                                          cent_salt=cent_salt)
                                    else:  # for AVISO
                                        if xi[centj, centi] <= 0.:  # Anticyclone
                                            A_list_obj.update_eddy_properties(centlon_e, centlat_e,
                                                                          eddy_radius_e, eddy_radius_e,
                                                                          amplitude, uavg, teke, rtime,)
                                        elif xi[centj, centi] >= 0.:  # Cyclone
                                            C_list_obj.update_eddy_properties(centlon_e, centlat_e,
                                                                          eddy_radius_e, eddy_radius_e,
                                                                          amplitude, uavg, teke, rtime,)

                                # Update SLA eddy properties
                                elif 'SLA' in Eddy.DIAGNOSTIC_TYPE:

                                    # See CSS11 section B4
                                    properties.centlon = np.copy(centlon_s)
                                    properties.centlat = np.copy(centlat_s)

                                    if has_ts: # for ocean model
                                        pass
                                        #if 'Anticyclonic' in sign_type:
                                            #A_list_obj.update_eddy_properties(centlon, centlat,
                                                                              #eddy_radius_s, eddy_radius_e,
                                                                              #amplitude, uavg, teke, rtime,
                                                                              #cent_temp=cent_temp,
                                                                              #cent_salt=cent_salt)
                                        #elif 'Cyclonic' in sign_type:
                                            #C_list_obj.update_eddy_properties(centlon, centlat,
                                                                              #eddy_radius_s, eddy_radius_e,
                                                                              #amplitude, uavg, teke, rtime,
                                                                              #cent_temp=cent_temp,
                                                                              #cent_salt=cent_salt)
                                    else:  # for AVISO

                                        if 'Anticyclonic' in sign_type:

                                            if A_list_obj.TRACK_EXTRA_VARIABLES:
                                                properties.contour_e = np.concatenate(
                                                    [contlon_e, contlat_e], axis=0)
                                                properties.contour_s = np.concatenate(
                                                    [contlon_s, contlat_s], axis=0)
                                            else:
                                                properties.contour_e = None
                                                properties.contour_s = None
                                                #properties.uavg_profile = None

                                            A_list_obj.update_eddy_properties(properties)

                                        elif 'Cyclonic' in sign_type:

                                            if C_list_obj.TRACK_EXTRA_VARIABLES:
                                                properties.contour_e = np.concatenate(
                                                    [contlon_e, contlat_e], axis=0)
                                                properties.contour_s = np.concatenate(
                                                    [contlon_s, contlat_s], axis=0)
                                            else:
                                                properties.contour_e = None
                                                properties.contour_s = None
                                                #properties.uavg_profile = None

                                            C_list_obj.update_eddy_properties(properties)

                                        #print '------- updated properties i %s seconds' %(time.time() - tt)

                                # Mask out already found eddies
                                if 'Q' in Eddy.DIAGNOSTIC_TYPE:
                                    xi[jmin:jmax, imin:imax].flat[mask_eff] = Eddy.FILLVAL

                                elif 'SLA' in Eddy.DIAGNOSTIC_TYPE:
                                    Eddy.sla[jmin:jmax, imin:imax][Eddy.mask_eff] = Eddy.FILLVAL

    # Leave collection_loop
    if 'SLA' in Eddy.DIAGNOSTIC_TYPE:
        if C_list_obj is None:
            return A_list_obj
        elif A_list_obj is None:
            return C_list_obj
    else:
        return A_list_obj, C_list_obj


def track_eddies(Eddy, first_record):
    """
    Track the eddies. First a distance matrix is calculated between
    all new and old eddies. Then loop through each old eddy, sorting the
    distances, and selecting that/those within range.
    """
    DIST0 = Eddy.DIST0
    AMP0 = Eddy.AMP0
    AREA0 = Eddy.AREA0
    #TEMP0 = 20.
    #SALT0 = 35.

    # True to debug
    debug_dist = False

    far_away = 1e9

    # We will need these in M for ellipse method below
    old_x, old_y = Eddy.M(np.array(Eddy.old_lon), np.array(Eddy.old_lat))
    new_x, new_y = Eddy.M(np.array(Eddy.new_lon_tmp),
                          np.array(Eddy.new_lat_tmp))

    #X_old = np.asfortranarray([Eddy.old_lon, Eddy.old_lat]).T
    X_old = np.asarray([Eddy.old_lon, Eddy.old_lat])
    #X_new = np.asfortranarray([Eddy.new_lon_tmp, Eddy.new_lat_tmp]).T
    X_new = np.asarray([Eddy.new_lon_tmp, Eddy.new_lat_tmp])

    # Use haversine distance for distance matrix between every old and new eddy
    #dist_mat = np.empty((X_old.shape[0], X_new.shape[0]), order='F')

    if first_record:
        # At first time step k and k+1 eddies are at the same places,
        # therefore move X_old a small distance away in preparation
        # for sparse matrix below.
        X_old += 0.01

    #haversine.distance_matrix(X_old, X_new, dist_mat)
    dist_mat = haversine.distance_matrix(X_old, X_new)
    #dist_mat = np.ascontiguousarray(dist_mat)
    
    dist_mat_copy = dist_mat.copy()

    #if np.any(dist_mat < 0): aaaaaaaaaaa
    # Prepare distance matrix for sparse operation
    # NOTE: need to find optimal (+dynamic) choice of filter here
    dist_mat[dist_mat > 200000.] = 0
    

    # Use a coordinate format (COO) sparse matrix
    # https://scipy-lectures.github.io/advanced/scipy_sparse/coo_matrix.html
    sparse_mat = sparse.coo_matrix((dist_mat))
    old_sparse_inds = sparse_mat.row
    new_sparse_inds = sparse_mat.col

    #print "old_sparse_inds=", old_sparse_inds
    #print "new_sparse_inds=", new_sparse_inds



    # *new_eddy_inds* contains indices to every newly identified eddy
    # that are initially set to True on the assumption that it is a new
    # eddy, i.e, it has just been born.
    # Later some will be set to False, indicating the continuation
    # of an existing eddy.
    new_eddy_inds = np.ones_like(new_x, dtype=bool)
    new_eddy = False

    # Loop over the old eddies looking for active eddies
    for old_ind in old_sparse_inds:

        dist_arr = np.array([])
        new_ln, new_lt, new_rd_s, new_rd_e, new_am, \
            new_Ua, new_ek, new_tm, new_tp, new_st = \
                [], [], [], [], [], [], [], [], [], []

        #if Eddy.TRACK_EXTRA_VARIABLES:
        #new_cntr_e, new_cntr_s, new_uavg_prf = [], [], []
        new_cntr_e, new_cntr_s = [], []
        new_shp_err = np.array([])

        #new_inds, backup_ind, backup_dist = np.array([], dtype=np.int16), \
                                            #np.array([], dtype=np.int16), \
                                            #np.array([])
        backup_ind = np.array([], dtype=np.int16)
        
        if debug_dist:
            debug_distmax = 5e6
            debug_cmap = plt.cm.Set3

            fig = plt.figure(225)
            #plt.clf()
            debug_ax = fig.add_subplot(131)
            #im = plt.imshow(dist_mat_copy, interpolation='none',
            #                origin='lower', cmap=debug_cmap)
            im = plt.matshow(dist_mat_copy,
                            origin='lower', cmap=debug_cmap)
            im.cmap.set_over('k')
            im.set_clim(0, debug_distmax)
            plt.colorbar()
            plt.xlabel('new')
            plt.ylabel('old')
            plt.title('original')
            plt.show()

        # Make an ellipse at current old_eddy location
        # (See CSS11 sec. B4, pg. 208)
        if 'ellipse' in Eddy.SEPARATION_METHOD:
            
            Eddy.search_ellipse.set_search_ellipse(old_x[old_ind],
                                                   old_y[old_ind])
            #Eddy.search_ellipse.view_search_ellipse(Eddy)

        # Loop over separation distances between old and new
        #for new_ind, new_dist in enumerate(dist_mat[old_ind]):
        for new_ind in new_sparse_inds:
            
            new_dist = dist_mat[old_ind, new_ind]
            within_range = False

            if new_dist < Eddy.search_ellipse.rw_c_mod: #far_away:

                if 'ellipse' in Eddy.SEPARATION_METHOD:
                    within_range = Eddy.search_ellipse.ellipse_path.contains_point(
                                            (new_x[new_ind], new_y[new_ind]))
                elif 'sum_radii' in Eddy.SEPARATION_METHOD:
                    sep_dist = Eddy.new_radii_tmp_e[new_ind]
                    sep_dist += Eddy.old_radii_e[old_ind]
                    sep_dist *= Eddy.sep_dist_fac
                    within_range = new_dist <= sep_dist
                else:
                    Exception

            # Pass only the eddies within ellipse or sep_dist
            if within_range:
                
                dist_arr = np.r_[dist_arr, new_dist]
                new_ln.append(Eddy.new_lon_tmp[new_ind])
                new_lt.append(Eddy.new_lat_tmp[new_ind])
                new_rd_s.append(Eddy.new_radii_s_tmp[new_ind])
                new_rd_e.append(Eddy.new_radii_e_tmp[new_ind])
                new_am.append(Eddy.new_amp_tmp[new_ind])
                new_Ua.append(Eddy.new_uavg_tmp[new_ind])
                new_ek.append(Eddy.new_teke_tmp[new_ind])
                new_tm.append(Eddy.new_time_tmp[new_ind])


                if 'ROMS' in Eddy.PRODUCT:
                    #new_tp = np.r_[new_tp, Eddy.new_temp_tmp[new_ind]]
                    #new_st = np.r_[new_st, Eddy.new_salt_tmp[new_ind]]
                    pass

                if Eddy.TRACK_EXTRA_VARIABLES:
                    new_cntr_e.append(Eddy.new_contour_e_tmp[new_ind])
                    new_cntr_s.append(Eddy.new_contour_s_tmp[new_ind])
                    #new_uavg_prf.append(Eddy.new_uavg_profile_tmp[new_ind])
                    new_shp_err = np.r_[new_shp_err,
                                        Eddy.new_shape_error_tmp[new_ind]]

                backup_ind = np.r_[backup_ind, new_ind]

                # An old (active) eddy has been detected, so
                # corresponding new_eddy_inds set to False
                # NOTE Versions 2.0.5 and prior used this redundancy
                #new_eddy_inds[np.nonzero(Eddy.new_lon_tmp ==
                                            #Eddy.new_lon_tmp[new_ind])] = False
                new_eddy_inds[new_ind] = False
                
                dist_mat[:, new_ind] = far_away # km
                    
        if Eddy.TRACK_EXTRA_VARIABLES:
            #kwargs = {'contour_e': new_cntr_e, 'contour_s': new_cntr_s,
                      #'uavg_profile': new_uavg_prf, 'shape_error': new_shp_err}
            kwargs = {'contour_e': new_cntr_e, 'contour_s': new_cntr_s,
                      'shape_error': new_shp_err}
        else:
            kwargs = {}

        # Only one eddy within range
        if dist_arr.size == 1:  # then update the eddy track only
            # Use index 0 here because type is list and we want the scalar
            args = (Eddy, old_ind, new_ln[0], new_lt[0], new_rd_s[0],
                    new_rd_e[0], new_am[0], new_Ua[0], new_ek[0], new_tm[0],
                    new_eddy, first_record)

            if 'ROMS' in Eddy.PRODUCT:
                pass
                #new_tp = new_st = 99; print 'correct me'
                #kwargs['cent_temp'] = new_tp[0]
                #kwargs['cent_salt'] = new_st[0]

            # NOTE accounting should be part of Eddy (or some other) object...
            Eddy = accounting(*args, **kwargs)

        # More than one eddy within range
        elif dist_arr.size > 1:

            # Loop to find the right eddy
            delta_area = np.array([])
            delta_amp = np.array([])
            delta_temp = np.array([])
            delta_salt = np.array([])

            for i in np.nditer(np.arange(dist_arr.size)):

                # Choice of using effective or speed-based...
                delta_area_tmp = np.array([np.pi *
                                           (Eddy.old_radii_e[old_ind] ** 2),
                                           np.pi * (new_rd_e[i] ** 2)]).ptp()
                delta_amp_tmp = np.array([Eddy.old_amp[old_ind],
                                          new_am[i]]).ptp()
                delta_area = np.r_[delta_area, delta_area_tmp]
                delta_amp = np.r_[delta_amp, delta_amp_tmp]

                if 'ROMS' in Eddy.PRODUCT:
                    #delta_temp_tmp = 
                    #delta_salt_tmp = 
                    pass
                    #delta_temp = np.r_[delta_temp,
                        #np.abs(np.diff([Eddy.old_temp[old_ind], new_tp[i]]))]
                    #delta_salt = np.r_[delta_salt,
                        #np.abs(np.diff([Eddy.old_salt[old_ind], new_st[i]]))]

            # This from Penven etal (2005)
            deltaX = np.sqrt((delta_area / AREA0) ** 2 +
                             (delta_amp / AMP0) ** 2 +
                             (dist_arr / DIST0) ** 2)

            dx = deltaX.argsort()
            dx0 = dx[0]  # index to the nearest eddy
            dx_unused = dx[1:]  # index/indices to the unused eddy/eddies

            if debug_dist:
                print('delta_area', delta_area)
                print('delta_amp', delta_amp)
                print('dist_arr', dist_arr)
                print('dx', dx)
                print('dx0', dx0)
                print('dx_unused', dx_unused)

            # Update eddy track dx0
            if not Eddy.TRACK_EXTRA_VARIABLES:
                new_cntr_e = new_cntr_s = new_uavg_prf = new_shp_err = None
            else:
                new_cntr_e = new_cntr_e[dx0]
                new_cntr_s = new_cntr_s[dx0]
                #new_uavg_prf = new_uavg_prf[dx0]
                new_shp_err = new_shp_err[dx0]

            args = (Eddy, old_ind, new_ln[dx0], new_lt[dx0], new_rd_s[dx0],
                    new_rd_e[dx0], new_am[dx0], new_Ua[dx0], new_ek[dx0],
                    new_tm[dx0], new_eddy, first_record)

            #kwargs = {'contour_e': new_cntr_e, 'contour_s': new_cntr_s,
                      #'uavg_profile': new_uavg_prf, 'shape_error': new_shp_err}
            kwargs = {'contour_e': new_cntr_e, 'contour_s': new_cntr_s,
                      'shape_error': new_shp_err}

            if 'ROMS' in Eddy.PRODUCT:
                pass
                #print 'fix me for temp and salt'

            Eddy = accounting(*args, **kwargs)

            if debug_dist:
                debug_ax = fig.add_subplot(132)
                im = plt.imshow(dist_mat, interpolation='none',
                                origin='lower', cmap=debug_cmap)
                im.cmap.set_over('k')
                im.set_clim(0, debug_distmax)
                plt.axis('image')
                plt.colorbar()
                plt.xlabel('new')
                plt.ylabel('old')
                plt.title('before')

            # Use backup_ind to reinsert distances into dist_mat for the unused eddy/eddies
            for bind in backup_ind[dx_unused]:
                dist_mat[:, bind] = dist_mat_copy[:, bind]
                new_eddy_inds[bind] = True

            if debug_dist:
                print('backup_ind', backup_ind)
                print('backup_ind[dx_unused]', backup_ind[dx_unused])
                print('backup_ind[dx_unused].shape', backup_ind[dx_unused].shape)
                debug_ax = fig.add_subplot(133)
                im = plt.imshow(dist_mat, interpolation='none',
                                origin='lower', cmap=debug_cmap)
                im.cmap.set_over('k')
                im.set_clim(0, debug_distmax)
                plt.axis('image')
                plt.colorbar()
                plt.xlabel('new')
                plt.ylabel('old')
                plt.title('after')
                plt.tight_layout()
                plt.show()
                plt.close(225)

    # Finished looping over old eddy tracks

    # Now we need to add new eddies defined by new_eddy_inds
    if np.any(new_eddy_inds):

        if False:
            print('------adding %s new eddies' % new_eddy_inds.sum())

        for neind, a_new_eddy in enumerate(new_eddy_inds):

            if a_new_eddy:  # Update the eddy tracks

                if not Eddy.TRACK_EXTRA_VARIABLES:
                    new_contour_e_tmp = new_contour_s_tmp = None
                    new_uavg_profile_tmp = new_shape_error_tmp = None

                else:
                    new_contour_e_tmp = Eddy.new_contour_e_tmp[neind]
                    new_contour_s_tmp = Eddy.new_contour_s_tmp[neind]
                    #new_uavg_profile_tmp = Eddy.new_uavg_profile_tmp[neind]
                    new_shape_error_tmp = Eddy.new_shape_error_tmp[neind]

                args = (Eddy, False, Eddy.new_lon_tmp[neind],
                        Eddy.new_lat_tmp[neind], Eddy.new_radii_s_tmp[neind],
                        Eddy.new_radii_e_tmp[neind], Eddy.new_amp_tmp[neind],
                        Eddy.new_uavg_tmp[neind], Eddy.new_teke_tmp[neind],
                        Eddy.new_time_tmp[neind], True, False)

                #kwargs = {'contour_e': new_contour_e_tmp,
                          #'contour_s': new_contour_s_tmp,
                          #'uavg_profile': new_uavg_profile_tmp,
                          #'shape_error': new_shape_error_tmp}
                kwargs = {'contour_e': new_contour_e_tmp,
                          'contour_s': new_contour_s_tmp,
                          'shape_error': new_shape_error_tmp}

                if 'ROMS' in Eddy.PRODUCT:
                    #kwargs['cent_temp'] = Eddy.new_temp_tmp[neind]
                    pass
                    #kwargs['cent_salt'] = Eddy.new_salt_tmp[neind]
                
                Eddy = accounting(*args, **kwargs)  
    
    return Eddy


def accounting(Eddy, old_ind, centlon, centlat,
               eddy_radius_s, eddy_radius_e, amplitude, uavg, teke, rtime,
               new_eddy, first_record, contour_e=None, contour_s=None,
               uavg_profile=None, shape_error=None, cent_temp=None,
               cent_salt=None):
    """
    Accounting for new or old eddy (either cyclonic or anticyclonic)
      Eddy  : eddy_tracker.tracklist object
      old_ind    : index to current old
      centlon, centlat: arrays of lon/lat centroids
      eddy_radius_s:  speed-based eddy radius
      eddy_radius_e:  effective eddy radius from fit_circle
      amplitude  :  eddy amplitude/intensity (max abs vorticity/f in eddy)
      uavg       :  average velocity within eddy contour
      teke       : sum of EKE within Ceff
      rtime      :  ROMS time in seconds
      cent_temp  :  array of temperature at centroids
      cent_salt  :  array of salinity at centroids
      bounds     :  index array(imin,imax,jmin,jmax) defining location of eddy
      new_eddy   : flag indicating a new eddy
      first_record : flag indicating that we're on the first record
    """
    #if teke == 999: print 'tekekkkkkkkkkkkkkkkkk'
    
    
    if first_record:  # is True then all eddies are new
        new_eddy = True
        if Eddy.VERBOSE:
            print('------ writing first record')

    #kwargs = {'temp': cent_temp, 'salt': cent_salt,
              #'contour_e': contour_e, 'contour_s': contour_s,
              #'uavg_profile': uavg_profile, 'shape_error': shape_error}
    kwargs = {'temp': cent_temp, 'salt': cent_salt,
              'contour_e': contour_e, 'contour_s': contour_s,
              'shape_error': shape_error}

    if not new_eddy:  # it's an old (i.e., active) eddy
        #if teke == 999: print 'oooooooooooooooooooooooooo'
        Eddy.insert_at_index('new_lon', old_ind, centlon)
        Eddy.insert_at_index('new_lat', old_ind, centlat)
        Eddy.insert_at_index('new_radii_s', old_ind, eddy_radius_s)
        Eddy.insert_at_index('new_radii_e', old_ind, eddy_radius_e)
        Eddy.insert_at_index('new_amp', old_ind, amplitude)
        Eddy.insert_at_index('new_uavg', old_ind, uavg)
        Eddy.insert_at_index('new_teke', old_ind, teke)

        if 'ROMS' in Eddy.PRODUCT:
            pass
            #Eddy.insert_at_index('new_temp', old_ind, cent_temp)
            #Eddy.insert_at_index('new_salt', old_ind, cent_salt)

        if Eddy.TRACK_EXTRA_VARIABLES:
            Eddy.insert_at_index('new_contour_e', old_ind, contour_e)
            Eddy.insert_at_index('new_contour_s', old_ind, contour_s)
            #Eddy.insert_at_index('new_uavg_profile', old_ind, uavg_profile)
            Eddy.insert_at_index('new_shape_error', old_ind, shape_error)

        args = (old_ind, centlon, centlat, rtime, uavg, teke,
                eddy_radius_s, eddy_radius_e, amplitude)

        Eddy.update_track(*args, **kwargs)

    else:  # it's a new eddy
        # We extend the range of array to old_ind
        Eddy.insert_at_index('new_lon', Eddy.index, centlon)
        Eddy.insert_at_index('new_lat', Eddy.index, centlat)
        Eddy.insert_at_index('new_radii_s', Eddy.index, eddy_radius_s)
        Eddy.insert_at_index('new_radii_e', Eddy.index, eddy_radius_e)
        Eddy.insert_at_index('new_amp', Eddy.index, amplitude)
        Eddy.insert_at_index('new_uavg', Eddy.index, uavg)
        Eddy.insert_at_index('new_teke', Eddy.index, teke)

        if 'ROMS' in Eddy.PRODUCT:
            #Eddy.insert_at_index('new_temp', Eddy.index, cent_temp)
            #Eddy.insert_at_index('new_salt', Eddy.index, cent_salt)
            pass

        if Eddy.TRACK_EXTRA_VARIABLES:
            Eddy.insert_at_index('new_contour_e', Eddy.index, contour_e)
            Eddy.insert_at_index('new_contour_s', Eddy.index, contour_s)
            #Eddy.insert_at_index('new_uavg_profile', Eddy.index, uavg_profile)
            Eddy.insert_at_index('new_shape_error', Eddy.index, shape_error)

        if Eddy.new_list:  # initialise a new list
            print(('------ starting a new track list for %s' %
                   Eddy.SIGN_TYPE.replace('nic', 'nes')))
            Eddy.new_list = False

        args = (centlon, centlat, rtime, uavg, teke,
                eddy_radius_s, eddy_radius_e, amplitude)

        Eddy.add_new_track(*args, **kwargs)

        Eddy.index += 1

    return Eddy  # Leave accounting


def get_ROMS_data(rfile, grd=None, index=None, sigma_lev=None,
                  DIAGNOSTIC_TYPE=None):
    """
    """
    with Dataset(rfile) as nc:

        if index is None:
            time = nc.variables['ocean_time'][:]
            return time

        time = nc.variables['ocean_time'][index]
        istr, iend = grd.ip0, grd.ip1
        jstr, jend = grd.jp0, grd.jp1
        if 'Q' in DIAGNOSTIC_TYPE:
            u = nc.variables['u'][index, sigma_lev, jstr:jend, istr:iend-1]
            v = nc.variables['v'][index, sigma_lev, jstr:jend-1, istr:iend]
            t = nc.variables['temp'][index, sigma_lev, jstr:jend, istr:iend]
            s = nc.variables['salt'][index, sigma_lev, jstr:jend, istr:iend]
            return u, v, t, s, time
        elif 'SLA' in DIAGNOSTIC_TYPE:
            zeta = nc.variables['zeta'][index, jstr:jend, istr:iend]
            return zeta, time
        else:
            return


def func_hann2d_fast(var, numpasses):
    """
    The treament of edges and corners in func_HANN2D can be mimicked by
    duplicating sides on to the W,E,S,N of the respective edges and
    replacing corner points with NaN's. Then smoothing can be done in
    a single step.
    Adapted from equivalent function in ETRACK.
    """
    jsz, isz = var.shape
    # Interior points  (N,S,W,E)
    nj = jsz + 2
    ni = isz + 2

    def hann2d_fast(var, ni, nj):
        #print 'jsz, isz',jsz, isz
        var_ext = np.ma.zeros((nj, ni))  # add 1-more line parallell to
        var_ext[1:-1, 1:-1] = var        # each of 4-sides
        var_ext[1:-1, 0] = var[:, 0]   # duplicate W-side
        var_ext[1:-1, -1] = var[:, -1]  # duplicate E-side
        var_ext[0, 1:-1] = var[0]   # duplicate N-side
        var_ext[-1, 1:-1] = var[-1]  # duplicate S-side
        var_ext[0, 0] = np.nan     # NW-corner
        var_ext[0, -1] = np.nan     # NE-corner
        var_ext[-1, 0] = np.nan     # SW-corner
        var_ext[-1, -1] = np.nan     # SE-corner

        # npts is used to count number of valid neighbors
        npts = ne.evaluate('var_ext * 0. + 1.')
        npts[np.isnan(npts)] = 0.

        # Replace nans with 0 to find a no-nan sum
        var_ext[np.isnan(var_ext)] = 0.

        # Initialize count and sum variables
        cc = np.ma.zeros((var.shape))
        varS = np.ma.zeros((var.shape))

        cc = npts[1:nj-1, 1:ni-1] * (npts[0:nj-2, 1:ni-1] + npts[2:nj, 1:ni-1] +
                                     npts[1:nj-1, 0:ni-2] + npts[1:nj-1, 2:ni])

        varS = (var_ext[0:nj-2, 1:ni-1] + var_ext[2:nj,   1:ni-1] + 
                var_ext[1:nj-1, 0:ni-2] + var_ext[1:nj-1, 2:ni])

        cc[cc == 0] = np.nan  # bring back nans in original data.
        weight = 8. - cc  # This is the weight for values on each grid point,
                                        # based on number of valid neighbours 
        # Final smoothed version of var
        hsm = 0.125 * (varS + weight * var_ext[1:jsz+1, 1:isz+1])
        return hsm

    for i in np.arange(numpasses):
        var[:] = hann2d_fast(var, ni, nj)

    return var


#def get_circle_OLD(x0, y0, r, npts):
    #"""
    #Return points on a circle, with specified (x0, y0) center and radius
                    #(and optional number of points too).

    #Input     : 1  - x0, scalar, center X of circle
                #2  - y0, scalar, center Y of circle
                #3  - r,  scalar, radius
                #4  - npts, scalar, number of points (optional)

    #Output    : 1  - cx, circle x-points
                #2  - cy, circle y-points

    #Example   :  [cx cy] = func_get_circle (5, 5, 3, 256)
                #plot (cx, cy, '-')

    #Written By : UCLA ROMS Team (jaison@atmos.ucla.edu)
    #Written On : June/05/2008
    #Tool       : Eddy Tracker
    #"""
    #theta = np.arange(np.float64(npts))  # NOTE npts is a constant, so
    ## *cos(theta)* and *sin(theta)* can be predefined
    ## SHOULD BE PART OF CONTOUR OBJECT
    #theta[:] = theta * 2. * (4. * np.arctan(1.)) / npts
    #cx = x0 + r * np.cos(theta)
    #cy = y0 + r * np.sin(theta)
    #return cx, cy


def get_circle(lon, lat, distance, npts):
    '''
    Given the inputs (base lon, base lat, angle [deg], distance [m]) return
    the lon, lat of the new position...
    # SHOULD BE PART OF CONTOUR OBJECT
    Could be speeded up with f2py
    '''
    pio180 = np.pi / 180.
    lon *= pio180
    lat *= pio180
    angle = np.arange(np.float64(npts))
    angle[:] = angle * 2. * (4. * np.arctan(1.)) / npts
    distance /= 6371315.0 # angular distance
    lat1 = (np.arcsin(np.sin(lat) * np.cos(distance) + np.cos(lat) *
                      np.sin(distance) * np.cos(angle)))
    lon1 = (lon + np.arctan2(np.sin(angle) * np.sin(distance) * np.cos(lat),
                             np.cos(distance) - np.sin(lat) * np.sin(lat1)))
    return lon1 / pio180, lat1 / pio180

