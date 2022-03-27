# PLBRenderer
This is a Blender renderer script for PLB, which serves as the server-side of the team's own [render protocol](https://github.com/fyp21011/RenderProtocol). 

## Testing

Change the directory to the repository root, i.e., the PLBRenderer folder. At one terminal, run: 

```sh
blender -b -P server.py
```

This will start the Blender as a server and waits connections from client. 

In another terminal, at the same directory, run:

```sh
python test_client.py
```

Once both the python and the blender processes exits, there will be a newly created file, named as `"test_XX.blend"`. This is a Blender file. Open it using Blender and you can view the animation or edit the scene. There will be rotation prism with a randomly generated sheet. 

<div align="center">
   <img src="https://user-images.githubusercontent.com/43565614/160277299-6896aa2d-77e6-4ea2-8a38-f9cb8985d4f6.gif" width=350/>
</div>

## Running

Start the server first using:

```sh

blender -b -P server.py
```

Then start the PlasticineLab engine, which will work as the client. When the engine is finished, the server will save the file as `"<exp_name>.blend"` and quit. 
