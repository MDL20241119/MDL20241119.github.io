CREATE TABLE `audit` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`actor` text NOT NULL,
	`action` text NOT NULL,
	`payload` text NOT NULL,
	`time` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `audit_owner_time` ON `audit` (`owner`,`time`);--> statement-breakpoint
CREATE TABLE `receipts` (
	`owner` text NOT NULL,
	`key` text NOT NULL,
	`command_id` text NOT NULL,
	`version` integer NOT NULL,
	`digest` text NOT NULL,
	`created_at` text NOT NULL,
	PRIMARY KEY(`owner`, `key`)
);
--> statement-breakpoint
CREATE TABLE `workspaces` (
	`owner` text PRIMARY KEY NOT NULL,
	`state` text NOT NULL,
	`version` integer NOT NULL
);
