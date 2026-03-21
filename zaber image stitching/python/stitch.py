from mist_stitching.main import mist
import argparse
import os

# Create arguments namespace
args = argparse.Namespace(
    image_dirpath=os.path.abspath('C:\\Users\\Admin\\Desktop\\zaber\\Images1'),  
    output_dirpath=os.path.abspath('C:\\Users\\Admin\\Desktop\\zaber\\Stitch_outputs_5'),
    grid_width=20,
    grid_height=20,
    filename_pattern='img_{:04d}.jpg',
    filename_pattern_type='SEQUENTIAL',
    grid_origin='UR',
    numbering_pattern='VERTICALCOMBING',  # Changed to match vertical scanning pattern
    save_image=True,
    output_prefix='',  # Empty prefix for simpler output names
    disable_mem_cache=False,
    start_tile=0,
    stage_repeatability=None,
    horizontal_overlap=None,
    vertical_overlap=None,
    overlap_uncertainty=3.0,
    valid_correlation_threshold=0.25,
    time_slice=0,
    translation_refinement_method='SINGLEHILLCLIMB',
    num_hill_climbs=16,
    num_fft_peaks=4
)

# Print debug information
print(f"Looking for images in: {args.image_dirpath}")
print(f"First expected filename: {args.filename_pattern.format(0)}")

# Run MIST stitching
if __name__ == "__main__":
    mist(args)