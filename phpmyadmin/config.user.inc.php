<?php
// Hardening phpMyAdmin
$cfg['Servers'][1]['AllowRoot'] = false;   // không cho đăng nhập bằng tài khoản root
$cfg['LoginCookieValidity'] = 1800;        // phiên hết hạn sau 30 phút
$cfg['ShowPhpInfo'] = false;
$cfg['ShowServerInfo'] = false;
