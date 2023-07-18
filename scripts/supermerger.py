import argparse
import gc
import os
import os.path
import re
import shutil
from importlib import reload
from pprint import pprint
import gradio as gr
from modules import (devices, script_callbacks, scripts, sd_hijack, sd_models,sd_vae, shared)
from modules.scripts import basedir
from modules.sd_models import checkpoints_loaded
from modules.shared import opts
from modules.ui import create_output_panel, create_refresh_button
import scripts.mergers.mergers
import scripts.mergers.pluslora
import scripts.mergers.xyplot
reload(scripts.mergers.mergers) # update without restarting web-ui.bat
reload(scripts.mergers.xyplot)
reload(scripts.mergers.pluslora)
import csv
import scripts.mergers.pluslora as pluslora
from scripts.mergers.mergers import (TYPESEG, freezemtime, rwmergelog, simggen,smergegen)
from scripts.mergers.xyplot import freezetime, nulister, numaker, numanager

gensets=argparse.Namespace()

def on_ui_train_tabs(params):
    txt2img_preview_params=params.txt2img_preview_params
    gensets.txt2img_preview_params=txt2img_preview_params
    return None

path_root = basedir()

def on_ui_tabs():
    weights_presets=""
    userfilepath = os.path.join(path_root, "scripts","mbwpresets.txt")
    if os.path.isfile(userfilepath):
        try:
            with open(userfilepath) as f:
                weights_presets = f.read()
                filepath = userfilepath
        except OSError as e:
                pass
    else:
        filepath = os.path.join(path_root, "scripts","mbwpresets_master.txt")
        try:
            with open(filepath) as f:
                weights_presets = f.read()
                shutil.copyfile(filepath, userfilepath)
        except OSError as e:
                pass

    with gr.Blocks() as supermergerui:
        with gr.Tab("Merge"):
            with gr.Row().style(equal_height=False):
                with gr.Column(scale = 3):
                    gr.HTML(value="<p>Merge models and load it for generation</p>")

                    with gr.Row():
                        model_a = gr.Dropdown(sd_models.checkpoint_tiles(),elem_id="model_converter_model_name",label="Model A",interactive=True)
                        create_refresh_button(model_a, sd_models.list_models,lambda: {"choices": sd_models.checkpoint_tiles()},"refresh_checkpoint_Z")

                        model_b = gr.Dropdown(sd_models.checkpoint_tiles(),elem_id="model_converter_model_name",label="Model B",interactive=True)
                        create_refresh_button(model_b, sd_models.list_models,lambda: {"choices": sd_models.checkpoint_tiles()},"refresh_checkpoint_Z")

                        model_c = gr.Dropdown(sd_models.checkpoint_tiles(),elem_id="model_converter_model_name",label="Model C",interactive=True)
                        create_refresh_button(model_c, sd_models.list_models,lambda: {"choices": sd_models.checkpoint_tiles()},"refresh_checkpoint_Z")

                    mode = gr.Radio(label = "Merge Mode",choices = ["Weight sum:A*(1-alpha)+B*alpha", "Add difference:A+(B-C)*alpha",
                                                        "Triple sum:A*(1-alpha-beta)+B*alpha+C*beta",
                                                        "sum Twice:(A*(1-alpha)+B*alpha)*(1-beta)+C*beta",
                                                         ], value = "Weight sum:A*(1-alpha)+B*alpha") 
                    calcmode = gr.Radio(label = "Calcutation Mode",choices = ["normal", "cosineA", "cosineB", "smoothAdd","tensor"], value = "normal") 
                    with gr.Row(): 
                        useblocks =  gr.Checkbox(label="use MBW")
                        base_alpha = gr.Slider(label="alpha", minimum=-1.0, maximum=2, step=0.001, value=0.5)
                        base_beta = gr.Slider(label="beta", minimum=-1.0, maximum=2, step=0.001, value=0.25)
                        #weights = gr.Textbox(label="weights,base alpha,IN00,IN02,...IN11,M00,OUT00,...,OUT11",lines=2,value="0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5")

                    with gr.Row():
                        merge = gr.Button(elem_id="model_merger_merge", value="Merge!",variant='primary')
                        mergeandgen = gr.Button(elem_id="model_merger_merge", value="Merge&Gen",variant='primary')
                        gen = gr.Button(elem_id="model_merger_merge", value="Gen",variant='primary')
                        stopmerge = gr.Button(elem_id="stopmerge", value="Stop",variant='primary')
                    with gr.Row():
                        with gr.Column(scale = 4):
                            save_sets = gr.CheckboxGroup(["save model", "overwrite","safetensors","fp16","save metadata"], value=["safetensors"], label="save settings")
                        with gr.Column(scale = 2):
                            id_sets = gr.CheckboxGroup(["image", "PNG info"], label="write merged model ID to")
                    with gr.Row():      
                        with gr.Column(min_width = 50, scale=2):
                            with gr.Row():
                                custom_name = gr.Textbox(label="Custom Name (Optional)", elem_id="model_converter_custom_name")
                                mergeid = gr.Textbox(label="merge from ID", elem_id="model_converter_custom_name",value = "-1")
                        with gr.Column(min_width = 50, scale=1):
                            with gr.Row():s_reverse= gr.Button(value="Set from ID(-1 for last)",variant='primary')

                    with gr.Accordion("Restore faces, Tiling, Hires. fix, Batch size",open = False):
                        batch_size = denois_str = gr.Slider(minimum=0, maximum=8, step=1, label='Batch size', value=1, elem_id="sm_txt2img_batch_size")
                        genoptions = gr.CheckboxGroup(label = "Gen Options",choices=["Restore faces", "Tiling", "Hires. fix"], visible = True,interactive=True,type="value")    
                        with gr.Row(elem_id="txt2img_hires_fix_row1", variant="compact"):
                            hrupscaler = gr.Dropdown(label="Upscaler", elem_id="txt2img_hr_upscaler", choices=[*shared.latent_upscale_modes, *[x.name for x in shared.sd_upscalers]], value=shared.latent_upscale_default_mode)
                            hr2ndsteps = gr.Slider(minimum=0, maximum=150, step=1, label='Hires steps', value=0, elem_id="txt2img_hires_steps")
                            denois_str = gr.Slider(minimum=0.0, maximum=1.0, step=0.01, label='Denoising strength', value=0.7, elem_id="txt2img_denoising_strength")
                            hr_scale = gr.Slider(minimum=1.0, maximum=4.0, step=0.05, label="Upscale by", value=2.0, elem_id="txt2img_hr_scale")
                            
                    hiresfix = [genoptions,hrupscaler,hr2ndsteps,denois_str,hr_scale]

                    with gr.Accordion("Elemental Merge",open = False):
                        with gr.Row():
                            esettings1 = gr.CheckboxGroup(label = "settings",choices=["print change"],type="value",interactive=True)
                        with gr.Row():
                            deep = gr.Textbox(label="Blocks:Element:Ratio,Blocks:Element:Ratio,...",lines=2,value="")
                    
                    with gr.Accordion("Tensor Merge",open = False,visible=False):
                        tensor = gr.Textbox(label="Blocks:Tensors",lines=2,value="")
                    
                    with gr.Row():
                        x_type = gr.Dropdown(label="X type", choices=[x for x in TYPESEG], value="alpha", type="index")
                        x_randseednum = gr.Number(value=3, label="number of -1", interactive=True, visible = True)
                    xgrid = gr.Textbox(label="Sequential Merge Parameters",lines=3,value="0.25,0.5,0.75")
                    y_type = gr.Dropdown(label="Y type", choices=[y for y in TYPESEG], value="none", type="index")    
                    ygrid = gr.Textbox(label="Y grid (Disabled if blank)",lines=3,value="",visible =False)
                    with gr.Row():
                        gengrid = gr.Button(elem_id="model_merger_merge", value="Sequential XY Merge and Generation",variant='primary')
                        stopgrid = gr.Button(elem_id="model_merger_merge", value="Stop XY",variant='primary')
                        s_reserve1 = gr.Button(value="Reserve XY Plot",variant='primary')
                    dtrue =  gr.Checkbox(value = True, visible = False)                
                    dfalse =  gr.Checkbox(value = False,visible = False)     
                    dummy_t =  gr.Textbox(value = "",visible = False)    
                blockid=["BASE","IN00","IN01","IN02","IN03","IN04","IN05","IN06","IN07","IN08","IN09","IN10","IN11","M00","OUT00","OUT01","OUT02","OUT03","OUT04","OUT05","OUT06","OUT07","OUT08","OUT09","OUT10","OUT11"]
        
                with gr.Column(scale = 2):
                    currentmodel = gr.Textbox(label="Current Model",lines=1,value="")  
                    submit_result = gr.Textbox(label="Message")
                    mgallery, mgeninfo, mhtmlinfo, mhtmllog = create_output_panel("txt2img", opts.outdir_txt2img_samples)
            with gr.Row(visible = False) as row_inputers:
                inputer = gr.Textbox(label="",lines=1,value="")
                addtox = gr.Button(value="Add to Sequence X")
                addtoy = gr.Button(value="Add to Sequence Y")
            with gr.Row(visible = False) as row_blockids:
                blockids = gr.CheckboxGroup(label = "block IDs",choices=[x for x in blockid],type="value",interactive=True)
            with gr.Row(visible = False) as row_calcmode:
                calcmodes = gr.CheckboxGroup(label = "calcmode",choices=["normal", "cosineA", "cosineB", "smoothAdd","tensor"],type="value",interactive=True)
            with gr.Row(visible = False) as row_checkpoints:
                checkpoints = gr.CheckboxGroup(label = "checkpoint",choices=[x.model_name for x in sd_models.checkpoints_list.values()],type="value",interactive=True)
            with gr.Row(visible = False) as row_esets:
                esettings = gr.CheckboxGroup(label = "effective chekcer settings",choices=["save csv","save anime gif","not save grid","print change"],type="value",interactive=True)
    
            with gr.Tab("Weights Setting"):
                with gr.Row():
                    setalpha = gr.Button(elem_id="copytogen", value="set to alpha",variant='primary')
                    readalpha = gr.Button(elem_id="copytogen", value="read from alpha",variant='primary')
                    setbeta = gr.Button(elem_id="copytogen", value="set to beta",variant='primary')
                    readbeta = gr.Button(elem_id="copytogen", value="read from beta",variant='primary')
                    setx = gr.Button(elem_id="copytogen", value="set to X",variant='primary')
                with gr.Row():
                    weights_a = gr.Textbox(label="weights for alpha, base alpha,IN00,IN02,...IN11,M00,OUT00,...,OUT11",value = "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5")
                    weights_b = gr.Textbox(label="weights,for beta, base beta,IN00,IN02,...IN11,M00,OUT00,...,OUT11",value = "0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2")
                with gr.Row():
                    base= gr.Slider(label="Base", minimum=0, maximum=1, step =0.01, value=0.5)
                    in00 = gr.Slider(label="IN00", minimum=0, maximum=1, step=0.01, value=0.5)
                    in01 = gr.Slider(label="IN01", minimum=0, maximum=1, step=0.01, value=0.5)
                    in02 = gr.Slider(label="IN02", minimum=0, maximum=1, step=0.01, value=0.5)
                    in03 = gr.Slider(label="IN03", minimum=0, maximum=1, step=0.01, value=0.5)
                with gr.Row():
                    in04 = gr.Slider(label="IN04", minimum=0, maximum=1, step=0.01, value=0.5)
                    in05 = gr.Slider(label="IN05", minimum=0, maximum=1, step=0.01, value=0.5)
                    in06 = gr.Slider(label="IN06", minimum=0, maximum=1, step=0.01, value=0.5)
                    in07 = gr.Slider(label="IN07", minimum=0, maximum=1, step=0.01, value=0.5)
                    in08 = gr.Slider(label="IN08", minimum=0, maximum=1, step=0.01, value=0.5)
                    in09 = gr.Slider(label="IN09", minimum=0, maximum=1, step=0.01, value=0.5)
                with gr.Row():
                    in10 = gr.Slider(label="IN10", minimum=0, maximum=1, step=0.01, value=0.5)
                    in11 = gr.Slider(label="IN11", minimum=0, maximum=1, step=0.01, value=0.5)
                    mi00 = gr.Slider(label="M00", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou00 = gr.Slider(label="OUT00", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou01 = gr.Slider(label="OUT01", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou02 = gr.Slider(label="OUT02", minimum=0, maximum=1, step=0.01, value=0.5)
                with gr.Row():
                    ou03 = gr.Slider(label="OUT03", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou04 = gr.Slider(label="OUT04", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou05 = gr.Slider(label="OUT05", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou06 = gr.Slider(label="OUT06", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou07 = gr.Slider(label="OUT07", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou08 = gr.Slider(label="OUT08", minimum=0, maximum=1, step=0.01, value=0.5)
                with gr.Row(): 
                    ou09 = gr.Slider(label="OUT09", minimum=0, maximum=1, step=0.01, value=0.5)       
                    ou10 = gr.Slider(label="OUT10", minimum=0, maximum=1, step=0.01, value=0.5)
                    ou11 = gr.Slider(label="OUT11", minimum=0, maximum=1, step=0.01, value=0.5)
            with gr.Tab("Weights Presets"):
                with gr.Row():
                    s_reloadtext = gr.Button(value="Reload Presets",variant='primary')
                    s_reloadtags = gr.Button(value="Reload Tags",variant='primary')
                    s_savetext = gr.Button(value="Save Presets",variant='primary')
                    s_openeditor = gr.Button(value="Open TextEditor",variant='primary')
                weightstags= gr.Textbox(label="available",lines = 2,value=tagdicter(weights_presets),visible =True,interactive =True) 
                wpresets= gr.TextArea(label="",value=weights_presets,visible =True,interactive  = True)    

            with gr.Tab("Reservation"):
                with gr.Row():
                    s_reserve = gr.Button(value="Reserve XY Plot",variant='primary')
                    s_reloadreserve = gr.Button(value="Reloat List",variant='primary')
                    s_startreserve = gr.Button(value="Start XY plot",variant='primary')
                    s_delreserve = gr.Button(value="Delete list(-1 for all)",variant='primary')
                    s_delnum = gr.Number(value=1, label="Delete num : ", interactive=True, visible = True,precision =0)
                with gr.Row():
                    numaframe = gr.Dataframe(
                        headers=["No.","status","xtype","xmenber", "ytype","ymenber","model A","model B","model C","alpha","beta","mode","use MBW","weights alpha","weights beta"],
                        row_count=5,)
            # with gr.Tab("manual"):
            #     with gr.Row():
            #         gr.HTML(value="<p> exampls: Change base alpha from 0.1 to 0.9 <br>0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9<br>If you want to display the original model as well for comparison<br>0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1</p>")
            #         gr.HTML(value="<p> For block-by-block merging <br>0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5<br>1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1<br>0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1</p>")
            
            with gr.Row():

                currentcache = gr.Textbox(label="Current Cache")
                loadcachelist = gr.Button(elem_id="model_merger_merge", value="Reload Cache List",variant='primary')
                unloadmodel = gr.Button(value="unload model",variant='primary')


        # main ui end 
    
        with gr.Tab("LoRA", elem_id="tab_lora"):
            pluslora.on_ui_tabs()

        with gr.Tab("History", elem_id="tab_history"):
            
            with gr.Row():
                load_history = gr.Button(value="load_history",variant='primary')
                searchwrods = gr.Textbox(label="",lines=1,value="")
                search = gr.Button(value="search")
                searchmode = gr.Radio(label = "Search Mode",choices = ["or","and"], value = "or",type  = "value") 
            with gr.Row():
                history = gr.Dataframe(
                        headers=["ID","Time","Name","Weights alpha","Weights beta","Model A","Model B","Model C","alpha","beta","Mode","use MBW","custum name","save setting","use ID"],
                )

        with gr.Tab("Elements", elem_id="tab_deep"):
                with gr.Row():
                    smd_model_a = gr.Dropdown(sd_models.checkpoint_tiles(),elem_id="model_converter_model_name",label="Checkpoint A",interactive=True)
                    create_refresh_button(smd_model_a, sd_models.list_models,lambda: {"choices": sd_models.checkpoint_tiles()},"refresh_checkpoint_Z")    
                    smd_loadkeys = gr.Button(value="load keys",variant='primary')
                with gr.Row():
                    keys = gr.Dataframe(headers=["No.","block","key"],)

        with gr.Tab("Metadeta", elem_id="tab_metadata"):
                with gr.Row():
                    meta_model_a = gr.Dropdown(sd_models.checkpoint_tiles(),elem_id="model_converter_model_name",label="read metadata",interactive=True)
                    create_refresh_button(meta_model_a, sd_models.list_models,lambda: {"choices": sd_models.checkpoint_tiles()},"refresh_checkpoint_Z")    
                    smd_loadmetadata = gr.Button(value="load keys",variant='primary')
                with gr.Row():
                    metadata = gr.TextArea()

        smd_loadmetadata.click(
            fn=loadmetadata,
            inputs=[meta_model_a],
            outputs=[metadata]
        )                 

        smd_loadkeys.click(
            fn=loadkeys,
            inputs=[smd_model_a],
            outputs=[keys]
        )

        def unload():
            if shared.sd_model == None: return "already unloaded"
            sd_hijack.model_hijack.undo_hijack(shared.sd_model)
            shared.sd_model = None
            gc.collect()
            devices.torch_gc()
            return "model unloaded"

        unloadmodel.click(fn=unload,outputs=[submit_result])

        load_history.click(fn=load_historyf,outputs=[history ])

        msettings=[weights_a,weights_b,model_a,model_b,model_c,base_alpha,base_beta,mode,calcmode,useblocks,custom_name,save_sets,id_sets,wpresets,deep,tensor]
        imagegal = [mgallery,mgeninfo,mhtmlinfo,mhtmllog]
        xysettings=[x_type,xgrid,y_type,ygrid,esettings]

        s_reverse.click(fn = reversparams,
            inputs =mergeid,
            outputs = [submit_result,*msettings[0:8],*msettings[9:13],deep,calcmode]
        )

        merge.click(
            fn=smergegen,
            inputs=[*msettings,esettings1,*gensets.txt2img_preview_params,*hiresfix,batch_size,currentmodel,dfalse],
            outputs=[submit_result,currentmodel]
        )

        mergeandgen.click(
            fn=smergegen,
            inputs=[*msettings,esettings1,*gensets.txt2img_preview_params,*hiresfix,batch_size,currentmodel,dtrue],
            outputs=[submit_result,currentmodel,*imagegal]
        )

        gen.click(
            fn=simggen,
            inputs=[*gensets.txt2img_preview_params,*hiresfix,batch_size,currentmodel,id_sets],
            outputs=[*imagegal],
        )

        s_reserve.click(
            fn=numaker,
            inputs=[*xysettings,*msettings,*gensets.txt2img_preview_params,*hiresfix,batch_size],
            outputs=[numaframe]
        )

        s_reserve1.click(
            fn=numaker,
            inputs=[*xysettings,*msettings,*gensets.txt2img_preview_params,*hiresfix,batch_size],
            outputs=[numaframe]
        )

        gengrid.click(
            fn=numanager,
            inputs=[dtrue,*xysettings,*msettings,*gensets.txt2img_preview_params,*hiresfix,batch_size],
            outputs=[submit_result,currentmodel,*imagegal],
        )

        s_startreserve.click(
            fn=numanager,
            inputs=[dfalse,*xysettings,*msettings,*gensets.txt2img_preview_params,*hiresfix,batch_size],
            outputs=[submit_result,currentmodel,*imagegal],
        )

        search.click(fn = searchhistory,inputs=[searchwrods,searchmode],outputs=[history])

        s_reloadreserve.click(fn=nulister,inputs=[dfalse],outputs=[numaframe])
        s_delreserve.click(fn=nulister,inputs=[s_delnum],outputs=[numaframe])
        loadcachelist.click(fn=load_cachelist,inputs=[],outputs=[currentcache])
        addtox.click(fn=lambda x:gr.Textbox.update(value = x),inputs=[inputer],outputs=[xgrid])
        addtoy.click(fn=lambda x:gr.Textbox.update(value = x),inputs=[inputer],outputs=[ygrid])

        stopgrid.click(fn=freezetime)
        stopmerge.click(fn=freezemtime)

        checkpoints.change(fn=lambda x:",".join(x),inputs=[checkpoints],outputs=[inputer])
        blockids.change(fn=lambda x:" ".join(x),inputs=[blockids],outputs=[inputer])
        calcmodes.change(fn=lambda x:",".join(x),inputs=[calcmodes],outputs=[inputer])

        menbers = [base,in00,in01,in02,in03,in04,in05,in06,in07,in08,in09,in10,in11,mi00,ou00,ou01,ou02,ou03,ou04,ou05,ou06,ou07,ou08,ou09,ou10,ou11]

        setalpha.click(fn=slider2text,inputs=menbers,outputs=[weights_a])
        setbeta.click(fn=slider2text,inputs=menbers,outputs=[weights_b])
        setx.click(fn=add_to_seq,inputs=[xgrid,weights_a],outputs=[xgrid])     

        readalpha.click(fn=text2slider,inputs=weights_a,outputs=menbers)
        readbeta.click(fn=text2slider,inputs=weights_b,outputs=menbers)

        x_type.change(fn=showxy,inputs=[x_type,y_type], outputs=[row_blockids,row_checkpoints,row_inputers,ygrid,row_esets,row_calcmode])
        y_type.change(fn=showxy,inputs=[x_type,y_type], outputs=[row_blockids,row_checkpoints,row_inputers,ygrid,row_esets,row_calcmode])
        x_randseednum.change(fn=makerand,inputs=[x_randseednum],outputs=[xgrid])

        import subprocess
        def openeditors():
            subprocess.Popen(['start', filepath], shell=True)

        def reloadpresets():
            try:
                with open(filepath) as f:
                    return f.read()
            except OSError as e:
                pass

        def savepresets(text):
            with open(filepath,mode = 'w') as f:
                f.write(text)

        s_reloadtext.click(fn=reloadpresets,inputs=[],outputs=[wpresets])
        s_reloadtags.click(fn=tagdicter,inputs=[wpresets],outputs=[weightstags])
        s_savetext.click(fn=savepresets,inputs=[wpresets],outputs=[])
        s_openeditor.click(fn=openeditors,inputs=[],outputs=[])

    return (supermergerui, "SuperMerger", "supermerger"),

msearch = []
mlist=[]

def loadmetadata(model):
    import json
    checkpoint_info = sd_models.get_closet_checkpoint_match(model)
    if ".safetensors" not in checkpoint_info.filename: return "no metadata(not safetensors)"
    sdict = sd_models.read_metadata_from_safetensors(checkpoint_info.filename)
    if sdict == {}: return "no metadata"
    return json.dumps(sdict,indent=4)

def load_historyf():
    filepath = os.path.join(path_root,"mergehistory.csv")
    global mlist,msearch
    msearch = []
    mlist=[]
    try:
        with  open(filepath, 'r') as f:
            reader = csv.reader(f)
            mlist =  [raw for raw in reader]
            mlist = mlist[1:]
            for m in mlist:
                msearch.append(" ".join(m))
            maxlen = len(mlist[-1][0])
            for i,m in enumerate(mlist):
                mlist[i][0] = mlist[i][0].zfill(maxlen)
            return mlist
    except:
        return [["no data","",""],]

def searchhistory(words,searchmode):
    outs =[]
    ando = "and" in searchmode
    words = words.split(" ") if " " in words else [words]
    for i, m in  enumerate(msearch):
        hit = ando
        for w in words:
            if ando:
                if w not in m:hit = False
            else:
                if w in m:hit = True
        print(i,len(mlist))
        if hit :outs.append(mlist[i])

    if outs == []:return [["no result","",""],]
    return outs

#msettings=[0 weights_a,1 weights_b,2 model_a,3 model_b,4 model_c,5 base_alpha,6 base_beta,7 mode,8 useblocks,9 custom_name,10 save_sets,11 id_sets,12 wpresets]

def reversparams(id):
    def selectfromhash(hash):
        for model in sd_models.checkpoint_tiles():
            if hash in model:
                return model
        return ""
    try:
        idsets = rwmergelog(id = id)
    except:
        return [gr.update(value = "ERROR: history file could not open"),*[gr.update() for x in range(14)]]
    if type(idsets) == str:
        print("ERROR")
        return [gr.update(value = idsets),*[gr.update() for x in range(14)]]
    if idsets[0] == "ID":return  [gr.update(value ="ERROR: no history"),*[gr.update() for x in range(14)]]
    mgs = idsets[3:]
    if mgs[0] == "":mgs[0] = "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5"
    if mgs[1] == "":mgs[1] = "0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2"
    mgs[2] = selectfromhash(mgs[2]) if len(mgs[2]) > 5 else ""
    mgs[3] = selectfromhash(mgs[3]) if len(mgs[3]) > 5 else ""
    mgs[4] = selectfromhash(mgs[4]) if len(mgs[4]) > 5 else ""
    mgs[8] = True if mgs[8] =="True" else False
    mgs[10] = mgs[10].replace("[","").replace("]","").replace("'", "") 
    mgs[10] = [x.strip() for x in mgs[10].split(",")]
    mgs[11] = mgs[11].replace("[","").replace("]","").replace("'", "") 
    mgs[11] = [x.strip() for x in mgs[11].split(",")]
    while len(mgs) < 14:
        mgs.append("")
    mgs[13] = "normal" if mgs[13] == "" else mgs[13] 
    return [gr.update(value = "setting loaded") ,*[gr.update(value = x) for x in mgs[0:14]]]

def add_to_seq(seq,maker):
    return gr.Textbox.update(value = maker if seq=="" else seq+"\r\n"+maker)

def load_cachelist():
    text = ""
    for x in checkpoints_loaded.keys():
        text = text +"\r\n"+ x.model_name
    return text.replace("\r\n","",1)

def makerand(num):
    text = ""
    for x in range(int(num)):
        text = text +"-1,"
    text = text[:-1]
    return text

#row_blockids,row_checkpoints,row_inputers,ygrid
def showxy(x,y):
    flags =[False]*6
    t = TYPESEG
    txy = t[x] + t[y]
    if "model" in txy : flags[1] = flags[2] = True
    if "pinpoint" in txy : flags[0] = flags[2] = True
    if "effective" in txy or "element" in txy : flags[4] = True
    if "calcmode" in txy : flags[5] = True
    if not "none" in t[y] : flags[3] = flags[2] = True
    return [gr.update(visible = x) for x in flags]

def text2slider(text):
    vals = [t.strip() for t in text.split(",")]
    return [gr.update(value = float(v)) for v in vals]

def slider2text(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z):
    numbers = [a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z]
    numbers = [str(x) for x in numbers]
    return gr.update(value = ",".join(numbers) )

def tagdicter(presets):
    presets=presets.splitlines()
    wdict={}
    for l in presets:
        w=[]
        if ":" in l :
            key = l.split(":",1)[0]
            w = l.split(":",1)[1]
        if "\t" in l:
            key = l.split("\t",1)[0]
            w = l.split("\t",1)[1]
        # if len([w for w in w.split(",")]) == 26:
        if len(w) == 26:
            wdict[key.strip()]=w
    return ",".join(list(wdict.keys()))

def loadkeys(model_a):
    checkpoint_info = sd_models.get_closet_checkpoint_match(model_a)
    sd = sd_models.read_state_dict(checkpoint_info.filename,"cpu")
    keys = []
    for i, key in enumerate(sd.keys()):
        re_inp = re.compile(r'\.input_blocks\.(\d+)\.')  # 12
        re_mid = re.compile(r'\.middle_block\.(\d+)\.')  # 1
        re_out = re.compile(r'\.output_blocks\.(\d+)\.') # 12

        weight_index = -1
        blockid=["BASE","IN00","IN01","IN02","IN03","IN04","IN05","IN06","IN07","IN08","IN09","IN10","IN11","M00","OUT00","OUT01","OUT02","OUT03","OUT04","OUT05","OUT06","OUT07","OUT08","OUT09","OUT10","OUT11","Not Merge"]

        NUM_INPUT_BLOCKS = 12
        NUM_MID_BLOCK = 1
        NUM_OUTPUT_BLOCKS = 12
        NUM_TOTAL_BLOCKS = NUM_INPUT_BLOCKS + NUM_MID_BLOCK + NUM_OUTPUT_BLOCKS

        if 'time_embed' in key:
            weight_index = -2                # before input blocks
        elif '.out.' in key:
            weight_index = NUM_TOTAL_BLOCKS - 1     # after output blocks
        else:
            m = re_inp.search(key)
            if m:
                inp_idx = int(m.groups()[0])
                weight_index = inp_idx
            else:
                m = re_mid.search(key)
                if m:
                    weight_index = NUM_INPUT_BLOCKS
                else:
                    m = re_out.search(key)
                    if m:
                        out_idx = int(m.groups()[0])
                        weight_index = NUM_INPUT_BLOCKS + NUM_MID_BLOCK + out_idx
        keys.append([i,blockid[weight_index+1],key])
    return keys

script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_train_tabs(on_ui_train_tabs)
