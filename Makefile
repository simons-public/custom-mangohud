all:
	pnpm i
	pnpm run build
	rsync -qr ../custom-mangohud deck@steamdeck:/home/deck/homebrew/plugins

sync:
	rsync -qr ../custom-mangohud deck@steamdeck:/home/deck/homebrew/plugins
