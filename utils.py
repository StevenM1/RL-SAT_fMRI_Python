import nipype
import nibabel as nib
import os
import random
import string
import glob

# make sure you dont input a 4D image
def apply_warp(img, sub,
               t1w_to_MNI=True, interpolation='Linear',
               trondheim_dir='/home/Public/trondheim'):
    ''' img can be a file path (preferred) OR a nifti1Image (which will be temporarily saved and then provided as a filepath to ants) '''
    from nipype.interfaces import ants

    if isinstance(img, str):
        if not os.path.exists(img):
            raise(IOError('img must either be a string pointing to an existing file, or a Nifti1Image. You passed: {}'.format(img)))
        input_is_img = False
    elif isinstance(img, nib.Nifti1Image):
        # save file, use a random string in name
        import random
        import string

        tmp1_name = './tmp_img_to_warp-{}.nii.gz'.format(''.join(random.choices(string.ascii_letters + string.digits, k=10)))
        img.to_filename(tmp1_name)  # save to temporary file
        img = tmp1_name
        input_is_img = True
    else:
        raise(IOError('Input type not understood... img must either be a string pointing to an existing file, or a Nifti1Header. You passed: {}'.format(img)))
    
    # find affine & composite warp
    if t1w_to_MNI:
        ## warping an img from functional T1w space (1.5 mm) to MNI2009c (1 mm)
        composite_warp_name = 'from-T1w_to-MNI152NLin2009cAsym'
        template_brain = os.path.join(trondheim_dir, 'sourcedata/templates/mni_icbm152_t1_tal_nlin_asym_09c_brain.nii')
        out_postfix = '_warped_2_MNI2009c'
    else:
        ## warping an img from MNI2009c (1 mm) to functional T1w space (1.5 mm)
        composite_warp_name = 'from-MNI152NLin2009cAsym_to-T1w'
        # use first bold_ref as reference img
        boldrefs = sorted(glob.glob(os.path.join(trondheim_dir, 'derivatives', 'fmriprep', 'fmriprep', f'sub-{sub}', 'ses-*', 'func', 
                                      f'sub-*_ses-*_task-*_run-1_space-T1w_boldref.nii.gz')))
        template_brain = boldrefs[0]
        out_postfix = f'_warped_2_T1w_sub-{sub}'

    composite_xfm = os.path.join(trondheim_dir, 'derivatives', 'fmriprep', 'fmriprep', f'sub-{sub}', 'anat', 
                             f'sub-{sub}_{composite_warp_name}_mode-image_xfm.h5')
    if not os.path.exists(composite_xfm):
        # if there's _only_ an anatomical session and no other sessions, the warp (.h5 file) is in a different place with a slightly different name...
        composite_xfm = os.path.join(trondheim_dir, 'derivatives', 'fmriprep', 'fmriprep', f'sub-{sub}', 'ses-anatomical', 'anat', 
                             f'sub-{sub}_ses-anatomical_{composite_warp_name}_mode-image_xfm.h5')
    
    output_img_name = os.path.basename(img).replace('.nii.gz', '') + out_postfix + '.nii.gz'
    
    # ants set-up
    warp = ants.ApplyTransforms()
    warp.inputs.input_image = img
    warp.inputs.input_image_type = 0
    warp.inputs.interpolation = interpolation
    warp.inputs.invert_transform_flags = [False] #,False]
    warp.inputs.reference_image = template_brain
    warp.inputs.out_postfix = out_postfix
    
    if t1w_to_MNI:
        warp.inputs.transforms = [composite_xfm]
    else:
        warp.inputs.transforms = [composite_xfm]
    
    res = warp.run()
    
    if input_is_img:
        os.remove(img)  # remove temporary file again, all we care is the output anyway
    return str(res.outputs.output_image)