-- Prosody XMPP Configuration for MAS-IFRS (SPADE 4.1.4)
-- Permite auto-registro aberto (in-band registration) sem necessidade de TLS em rede interna

admins = { }
modules_enabled = {
    "roster";
    "saslauth";
    "tls";
    "dialback";
    "disco";
    "posix";
    "private";
    "vcard4";
    "version";
    "uptime";
    "time";
    "ping";
    "register";
    "admin_adhoc";
};

modules_disabled = { };

allow_registration = true;
c2s_require_encryption = false;
s2s_require_encryption = false;
allow_unencrypted_plain_auth = true;
authentication = "internal_plain";

log = {
    info = "*console";
    error = "*console";
}

VirtualHost "localhost"
    allow_registration = true;
    allow_unencrypted_plain_auth = true;
    authentication = "internal_plain";

VirtualHost "xmpp"
    allow_registration = true;
    allow_unencrypted_plain_auth = true;
    authentication = "internal_plain";
