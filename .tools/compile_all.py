import py_compile,sys,os
errors=0
for root,dirs,files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            path=os.path.join(root,f)
            try:
                py_compile.compile(path,doraise=True)
            except Exception as e:
                print('ERROR compiling',path,':',e)
                errors+=1
if errors:
    sys.exit(1)
print('All .py files compiled successfully')
