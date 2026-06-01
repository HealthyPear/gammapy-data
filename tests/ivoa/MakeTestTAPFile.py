#!/usr/bin/env python
# coding: utf-8

# # Setup 

from pathlib import Path
from pyvo import dal


target_name = "Crab"
save_dir = Path("tap_ds_test/")
save_dir.mkdir(parents=True, exist_ok=True)

tap_service = dal.TAPService("http://voparis-tap-he.obspm.fr/tap")
get_crab = "SELECT * FROM hess_dr.obscore WHERE 1=CONTAINS(POINT('ICRS',hess_dr.obscore.s_ra,hess_dr.obscore.s_dec),CIRCLE('ICRS',82.013336,22.014444,5))"

tap_result = tap_service.search(get_crab)


# # Make obscore_table.fits.gz

from astropy.table import Column, Table
from gammapy.data.ivoa import to_obscore_table


root_dir = Path(os.path.expandvars("$GAMMAPY_DATA")) / "hess-dl3-dr1/"
obs_core_tab = to_obscore_table(root_dir)

restab = tap_result.to_table()
sel = obs_core_tab["target_name"] == "Crab Nebula"
crabs = obs_core_tab[sel]
crabs.add_columns(
    restab[
        "ra_pnt",
        "dec_pnt",
        "alt_pnt",
        "az_pnt",
        "tstart",
        "tstop",
    ].columns
)
for coln in [
    "date_obs",
    "time_obs",
    "date_end",
    "time_end",
]:
    c = Column(restab[coln].data, dtype=str, name=coln)
    crabs.add_columns([c])

crabs.write("obscore_table.fits.gz", overwrite=False)


# # Make split irf files
from astropy.io import fits


HDU_TYPES = {
    "EFF_AREA": "aeff",
    "EDISP": "edisp",
    "PSF": "psf",
    "RPSF": "psf",
    "BKG": "bkg",
    "RAD_MAX": "rad_max",
}
out_pattern = "TapResult-{}-{}.fits.gz"


ds = Table.read(root_dir / "hdu-index.fits.gz")
data_dir = ds["FILE_DIR"][0]

# # Make bundled irf files
run_ids = ["23523", "23526", "23559", "23592"]
for obsid in run_ids:
    sel = (ds["OBS_ID"] == int(obsid)) & (ds["HDU_CLASS"] == "events")
    input_fil = ds["FILE_NAME"][sel].pformat(show_name=False)[0]
    out_hdus = []
    with fits.open(root_dir / data_dir / str(input_fil)) as hdus:
        out_hdus = []
        for hdu in hdus:
            hdu.data = None
            out_hdus.append(hdu)

        out_name = out_pattern.format(obsid, "event-bundle")
        fits.HDUList(out_hdus).writeto(out_name)


# # Make split irf files
run_ids = ["23559", "23592"]
for obsid in run_ids:
    sel = (ds["OBS_ID"] == int(obsid)) & (ds["HDU_CLASS"] == "events")
    input_fil = ds["FILE_NAME"][sel].pformat(show_name=False)[0]
    out_hdus = []
    with fits.open(root_dir / data_dir / str(input_fil)) as hdus:
        for hdu in hdus:
            out_name = ""
            if hdu.name == "PRIMARY":
                primary = hdu
                continue
            if hdu.name == "EVENTS":
                hdu.data = None
                out_hdus.append(hdu)
                continue
            elif hdu.name == "GTI":
                hdu.data = None
                out_hdus.append(hdu)
                phdu = primary.copy()
                out_fits = fits.HDUList([phdu] + out_hdus)
                out_name = out_pattern.format(obsid, "event-list")
            else:
                phdu = primary.copy()
                hdu.data = None
                out_fits = fits.HDUList([phdu, hdu])
                out_name = out_pattern.format(
                    obsid, HDU_TYPES[hdu.header["HDUCLAS2"].strip()]
                )
            print(out_name)
            out_fits.writeto(out_name)


# # Make datalink.xml

for idx, row in enumerate(tap_result):
    print(f"datalink_{idx}.xml")
    row.getdatalink().votable.to_xml(f"datalink_{idx}.xml")


# # Make split_datalink.xml

replace = {
    0: "obs_id",
    1: "aeff",
    2: "edisp",
    3: "psf",
    4: "bkg",
}
counter = 0
edited = []

with open("datalink_2.xml", "r") as fil:
    dltxt = fil.readlines()

for idx, line in enumerate(dltxt):
    if idx > 166 and idx < 179:
        continue

    if "fits.gz" in line:
        line = line.replace("obs_id", replace[counter])
        counter += 1

    edited.append(line)

with open("split_datalink_1.xml","w") as fil:
    fil.writelines(edited)

with open("datalink_3.xml", "r") as fil:
    dltxt = fil.readlines()

counter = 0
edited = []
for idx, line in enumerate(dltxt):
    if idx > 166 and idx < 179:
        continue

    if "fits.gz" in line:
        line = line.replace("obs_id", replace[counter])
        counter += 1

    edited.append(line)

with open("split_datalink_2.xml","w") as fil:
    fil.writelines(edited)
