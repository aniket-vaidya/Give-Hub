-- Create the database if it doesn't exist and then select it.
CREATE DATABASE IF NOT EXISTS givehub_db;
USE givehub_db;

-- -----------------------------------------------------
-- Table `users`
-- Stores login information for all roles.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL,
  `role` VARCHAR(50) NOT NULL COMMENT 'Can be Admin, Donor, NGO, Medical Store, Central Hub',
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`));


-- -----------------------------------------------------
-- Table `medical_stores`
-- Stores details for medical store partners, including location.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `medical_stores` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `contact_number` VARCHAR(20) NULL,
  `address` TEXT NULL,
  `pincode` VARCHAR(10) NULL,
  `latitude` DECIMAL(10, 8) NULL,
  `longitude` DECIMAL(11, 8) NULL,
  `approved` TINYINT(1) NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `fk_medical_stores_users_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `fk_medical_stores_users`
    FOREIGN KEY (`user_id`)
    REFERENCES `givehub_db`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `ngos`
-- Stores details for NGO partners, including location.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `ngos` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `contact_person` VARCHAR(255) NULL,
  `contact_number` VARCHAR(20) NULL,
  `address` TEXT NULL,
  `registration_number` VARCHAR(255) NULL,
  `pincode` VARCHAR(10) NULL,
  `latitude` DECIMAL(10, 8) NULL,
  `longitude` DECIMAL(11, 8) NULL,
  `approved` TINYINT(1) NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `fk_ngos_users_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `fk_ngos_users`
    FOREIGN KEY (`user_id`)
    REFERENCES `givehub_db`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `donations`
-- Main record for each donation instance.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `donations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `donor_name` VARCHAR(255) NOT NULL,
  `contact_number` VARCHAR(20) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `address` TEXT NOT NULL,
  `medical_store_id` INT NOT NULL,
  `status` VARCHAR(50) NULL DEFAULT 'Pending',
  `medical_store_status` VARCHAR(50) NULL,
  `central_hub_status` VARCHAR(50) NULL,
  `certificate_path` VARCHAR(255) NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_donations_medical_stores_idx` (`medical_store_id` ASC) VISIBLE,
  CONSTRAINT `fk_donations_medical_stores`
    FOREIGN KEY (`medical_store_id`)
    REFERENCES `givehub_db`.`medical_stores` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `donation_medicines`
-- Stores each individual medicine within a donation.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `donation_medicines` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `donation_id` INT NOT NULL,
  `medicine_name` VARCHAR(255) NOT NULL,
  `quantity` INT NOT NULL,
  `batch_no` VARCHAR(100) NULL,
  `expiry_date` DATE NOT NULL,
  `image_filename` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_donation_medicines_donations_idx` (`donation_id` ASC) VISIBLE,
  CONSTRAINT `fk_donation_medicines_donations`
    FOREIGN KEY (`donation_id`)
    REFERENCES `givehub_db`.`donations` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `requests`
-- Main record for each medicine request from an NGO.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `requests` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `requester_id` INT NOT NULL COMMENT 'This is the user_id of the NGO',
  `medical_store_id` INT NULL,
  `num_beneficiaries` INT NULL,
  `requester_name` VARCHAR(255) NULL,
  `contact_number` VARCHAR(20) NULL,
  `address` TEXT NULL,
  `status` VARCHAR(50) NOT NULL DEFAULT 'Pending',
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_requests_users_idx` (`requester_id` ASC) VISIBLE,
  INDEX `fk_requests_medical_stores_idx` (`medical_store_id` ASC) VISIBLE,
  CONSTRAINT `fk_requests_users`
    FOREIGN KEY (`requester_id`)
    REFERENCES `givehub_db`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_requests_medical_stores`
    FOREIGN KEY (`medical_store_id`)
    REFERENCES `givehub_db`.`medical_stores` (`id`)
    ON DELETE SET NULL
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `request_beneficiaries`
-- Stores details for each beneficiary in a request.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `request_beneficiaries` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `request_id` INT NOT NULL,
  `beneficiary_name` VARCHAR(255) NOT NULL,
  `age` INT NOT NULL,
  `sex` VARCHAR(20) NOT NULL,
  `doctor_prescription_path` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_request_beneficiaries_requests_idx` (`request_id` ASC) VISIBLE,
  CONSTRAINT `fk_request_beneficiaries_requests`
    FOREIGN KEY (`request_id`)
    REFERENCES `givehub_db`.`requests` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `request_medicines`
-- Stores each medicine needed for a specific request.
-- Note: This is simplified. For the dynamic form, you might link this to `request_beneficiaries` instead.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `request_medicines` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `request_id` INT NOT NULL,
  `medicine` VARCHAR(255) NOT NULL,
  `quantity` INT NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_request_medicines_requests_idx` (`request_id` ASC) VISIBLE,
  CONSTRAINT `fk_request_medicines_requests`
    FOREIGN KEY (`request_id`)
    REFERENCES `givehub_db`.`requests` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);


-- -----------------------------------------------------
-- Table `central_inventory`
-- Stock held at the central GiveHub facility.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `central_inventory` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `medicine_name` VARCHAR(255) NOT NULL,
  `quantity` INT NOT NULL,
  `batch_no` VARCHAR(100) NULL,
  `expiry_date` DATE NOT NULL,
  `unit_price` DECIMAL(10,2) NULL,
  `current_location` VARCHAR(255) NULL,
  `received_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`));


-- -----------------------------------------------------
-- Table `medical_store_stock`
-- Stock held at individual partner medical stores.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `medical_store_stock` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `medical_store_id` INT NOT NULL,
  `medicine_name` VARCHAR(255) NOT NULL,
  `quantity` INT NOT NULL,
  `batch_no` VARCHAR(100) NULL,
  `expiry_date` DATE NOT NULL,
  `unit_price` DECIMAL(10,2) NULL,
  `received_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_medical_store_stock_medical_stores_idx` (`medical_store_id` ASC) VISIBLE,
  CONSTRAINT `fk_medical_store_stock_medical_stores`
    FOREIGN KEY (`medical_store_id`)
    REFERENCES `givehub_db`.`medical_stores` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION);
