set modelpath=%1
set reebpath=%2
pushd "%~dp0"
java -Xmx3g -classpath recon.jar vgl.iisc.cmd.ReCon %modelpath% %reebpath%
popd