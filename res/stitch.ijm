args = getArgument();
a = split(args, " ");
file = a[0];

channelKnown = 0;
isRGB = 0;

if(a.length>1)
{
    channel = a[1];
    // TODO: is there an equals in ImageJ?
    isRGB = startsWith(channel, "RGB") & endsWith(channel, "RGB");
    channelKnown = 1;
}

lastDelim = lastIndexOf(file, "/");
directory = substring(file, 0, lastDelim);

// -------- define dataset -----------
run("Define dataset ...", "define_dataset=[Automatic Loader (Bioformats based)] project_filename=dataset.xml path="+file+" exclude=10 bioformats_series_are?=Tiles move_tiles_to_grid_(per_angle)?=[Do not move Tiles to Grid (use Metadata if available)] how_to_load_images=[Load raw data] dataset_save_path="+file+"_stitched check_stack_sizes");

// greyscale cam was used -> flip x axis
if(!isRGB)
{
   run("Flip Axes", "select="+file+"_stitched/dataset.xml flip_x");
}

// use average of channels for stitching if we have RGB or user did not specify which channel to use
if(isRGB | !channelKnown)
{
    channelString = "[Average Channels]";
}
else
{
    channelString = "[use Channel " + channel + "]";
}

// --------- calculate shifts ----------
run("Calculate pairwise shifts ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] method=[Phase Correlation] channels=" + channelString + " downsample_in_x=4 downsample_in_y=4 downsample_in_z=2");

// ----------- filter --------------
// filter by r > .4
run("Filter pairwise shifts ...", "select="+file+"_stitched/dataset.xml filter_by_link_quality min_r=0.40 max_r=1 max_shift_in_x=0 max_shift_in_y=0 max_shift_in_z=0 max_displacement=0");

// ----------- global opt -------------
// we do unnecessary expert grouping here, but it is neccessary to prevent a bug in BigStitcher < 0.1.16
//run("Optimize globally and apply shifts ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] relative=2.500 absolute=3.500 global_optimization_strategy=[Two-Round using Metadata to align unconnected Tiles] show_expert_grouping_options how_to_treat_timepoints=[treat individually] how_to_treat_channels=group how_to_treat_illuminations=group how_to_treat_angles=[treat individually] how_to_treat_tiles=compare fix_group_0-0,");
run("Optimize globally and apply shifts ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] relative=2.500 absolute=3.500 global_optimization_strategy=[Two-Round using Metadata to align unconnected Tiles]");


// greyscale cam was used -> mirror everything so we get original orientation in result
if(!isRGB)
{
    run("Apply Transformations", "select="+file+"_stitched/dataset.xml apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_channels same_transformation_for_all_tiles timepoint_0_all_channels_illumination_0_angle_0=[-1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]");
}


// --------- fuse -------------
// note that this requires multiview-reconstruction >= 0.1.18
//("Fuse dataset ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] bounding_box=[All Views] downsampling=1 pixel_type=[16-bit unsigned integer] interpolation=[Linear Interpolation] image=[Precompute Image] blend preserve_original produce=[Each timepoint & channel] fused_image=[Save as (compressed) TIFF stacks] output_file_directory="+file+"_stitched/");
run("Fuse dataset ...", "select="+file+"_stitched/dataset.xml process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints] bounding_box=[All Views] downsampling=1 pixel_type=[16-bit unsigned integer] interpolation=[Linear Interpolation] image=[Precompute Image] interest_points_for_non_rigid=[-= Disable Non-Rigid =-] blend preserve_original produce=[Each timepoint & channel] fused_image=[Save as (compressed) TIFF stacks] output_file_directory="+file+"_stitched/ filename_addition=[]");

eval("script", "System.exit(0);");
