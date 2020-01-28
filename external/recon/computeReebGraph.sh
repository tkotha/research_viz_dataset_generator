pushd "%~dp0"
java -Xmx3g -classpath recon.jar vgl.iisc.cmd.ReCon $1 $2
popd