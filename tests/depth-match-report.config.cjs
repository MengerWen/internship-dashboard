const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
 testDir:'.',testMatch:'depth-match-report.spec.cjs',workers:1,timeout:45000,
 use:{headless:true,viewport:{width:1440,height:1000}},
 webServer:{command:'python -m http.server 8767 --bind 127.0.0.1',cwd:require('path').resolve(__dirname,'..'),url:'http://127.0.0.1:8767',reuseExistingServer:false}
});
