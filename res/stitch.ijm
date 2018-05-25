file = getArgument()
lastDelim = lastIndexOf(file, "/");
directory = substring(file, 0, lastDelim);

// -------- define dataset -----------
// note that because of incorrect loading of ND2 metadata, we apply 100% overlap
// that way, we have to do more calculations, but it works
// TODO: fix in loader!
// changes in dialogs from multiview-reconstruction > 0.2.2
run("Define dataset ...", "define_dataset=[Automatic Loader (Bioformats based)]project_filename=dataset.xml path="+file+" exclude=10 bioformats_series_are?=Tiles move_tiles_to_grid_(per_angle)?=[Move Tile to Grid (Macro-scriptable)] grid_type=[Right & Down             ] tiles_x=50 tiles_y=50 tiles_z=1 overlap_x_(%)=100 overlap_y_(%)=100 overlap_z_(%)=0 keep_metadata_rotation how_to_load_images=[Load raw data virtually (with caching)] dataset_save_path="+file+"_stitched");

// --------- calculate shifts ----------
run("Calculate pairwise shifts ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] method=[Phase Correlation] channels=[use Channel DIA10x] downsample_in_x=4 downsample_in_y=4 downsample_in_z=2");

// ----------- filter --------------
// filter by r > .4
run("Filter pairwise shifts ...", "select="+file+"_stitched/dataset.xml filter_by_link_quality min_r=0.40 max_r=1 max_shift_in_x=0 max_shift_in_y=0 max_shift_in_z=0 max_displacement=0");

// ----------- global opt -------------
// we do unnecessary expert grouping here, but it is neccessary to prevent a bug in BigStitcher < 0.1.16
run("Optimize globally and apply shifts ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] relative=2.500 absolute=3.500 global_optimization_strategy=[Two-Round using Metadata to align unconnected Tiles] show_expert_grouping_options how_to_treat_timepoints=[treat individually] how_to_treat_channels=group how_to_treat_illuminations=group how_to_treat_angles=[treat individually] how_to_treat_tiles=compare fix_group_0-0,");

// --------- fuse -------------
// note that this requires multiview-reconstruction >= 0.1.18
run("Fuse dataset ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] bounding_box=[All Views] downsampling=1 pixel_type=[16-bit unsigned integer] interpolation=[Linear Interpolation] image=[Precompute Image] blend preserve_original produce=[Each timepoint & channel] fused_image=[Save as (compressed) TIFF stacks] output_file_directory="+file+"_stitched/");

eval("script", "System.exit(0);");
