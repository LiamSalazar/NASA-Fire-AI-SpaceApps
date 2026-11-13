import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'**/*.spec.js',timeout:240000,workers:1,retries:0,reporter:[['list'],['json',{outputFile:'../../artifacts/product_finalize_20261113/browser-results.json'}]],use:{baseURL:'http://127.0.0.1:5173',viewport:{width:1440,height:1000},screenshot:'only-on-failure',trace:'retain-on-failure'}});
