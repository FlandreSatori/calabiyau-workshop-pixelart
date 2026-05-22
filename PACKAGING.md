打包说明

1.  ```
    pyinstaller -w --clean --onefile run_app.py
    ```

2.  ```
    pyinstaller --clean --onefile --name backend backend/main.py
    ```

3.  ```
     cd frontend
     npm run tauri build
    ```

4. 把```frontend\src-tauri\target\release\frontend.exe```下的复制到```\dist```

5. 把```dd.54900.dll```下的复制到```\dist```

6. 运行```run_app.exe```
