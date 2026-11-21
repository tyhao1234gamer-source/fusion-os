################################################################################
#
# ostree
#
################################################################################

OSTREE_VERSION = 2026.7
OSTREE_SITE = https://github.com/ostreedev/ostree/releases/download/v$(OSTREE_VERSION)
OSTREE_SOURCE = libostree-$(OSTREE_VERSION).tar.xz
OSTREE_LICENSE = LGPL-2.0+
OSTREE_LICENSE_FILES = COPYING
OSTREE_INSTALL_STAGING = YES
OSTREE_DEPENDENCIES = \
	host-bison \
	host-libglib2 \
	host-pkgconf \
	libglib2 \
	xz \
	zlib \
	e2fsprogs \
	libgpgme \
	libcurl \
	libarchive \
	util-linux

OSTREE_CONF_OPTS = \
	--with-curl \
	--without-soup \
	--without-soup3 \
	--with-gpgme \
	--with-libarchive \
	--with-libmount \
	--with-crypto=glib \
	--without-openssl \
	--without-selinux \
	--without-smack \
	--without-avahi \
	--without-composefs \
	--without-ed25519-libsodium \
	--without-dracut \
	--without-mkinitcpio \
	--disable-rofiles-fuse \
	--disable-man \
	--disable-man-html \
	--disable-gtk-doc \
	--disable-introspection \
	--disable-sanitizers

ifeq ($(BR2_PACKAGE_SYSTEMD),y)
OSTREE_CONF_OPTS += --with-libsystemd
OSTREE_DEPENDENCIES += systemd
else
OSTREE_CONF_OPTS += --without-libsystemd
endif

$(eval $(autotools-package))
