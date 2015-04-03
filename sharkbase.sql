-- phpMyAdmin SQL Dump
-- version 3.5.8.1
-- http://www.phpmyadmin.net
--
-- Host: :/cloudsql/sql-fortress:fortress-one
-- Generation Time: Apr 03, 2015 at 12:59 AM
-- Server version: 5.5.38
-- PHP Version: 5.4.35

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `sharkbase`
--

-- --------------------------------------------------------

--
-- Table structure for table `books`
--

CREATE TABLE IF NOT EXISTS `books` (
  `BID` int(11) NOT NULL AUTO_INCREMENT,
  `author` varchar(255) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `link` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`BID`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=16 ;

-- --------------------------------------------------------

--
-- Table structure for table `categories`
--

CREATE TABLE IF NOT EXISTS `categories` (
  `CatID` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL,
  UNIQUE KEY `CatID` (`CatID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `companies`
--

CREATE TABLE IF NOT EXISTS `companies` (
  `COID` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `people` varchar(255) NOT NULL,
  `category` varchar(255) NOT NULL,
  `description` varchar(510) NOT NULL,
  `deal` tinyint(1) NOT NULL,
  `status` varchar(255) DEFAULT NULL,
  `website` varchar(255) NOT NULL,
  `amazon` varchar(255) DEFAULT NULL,
  `walmart` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`COID`),
  UNIQUE KEY `COID` (`COID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `deals`
--

CREATE TABLE IF NOT EXISTS `deals` (
  `DID` varchar(255) NOT NULL,
  `COID` varchar(255) NOT NULL,
  `EPID` varchar(255) NOT NULL,
  `deal_pct` float NOT NULL,
  `funded` int(11) DEFAULT NULL COMMENT '1 = yes, 0 = no, NULL = unknown',
  `deal_usd` int(11) NOT NULL,
  `bcorcoran` int(11) NOT NULL DEFAULT '0',
  `djohn` int(11) NOT NULL DEFAULT '0',
  `koleary` int(11) NOT NULL DEFAULT '0',
  `rherjavec` int(11) NOT NULL DEFAULT '0',
  `kharrington` int(11) NOT NULL DEFAULT '0',
  `lgreiner` int(11) NOT NULL DEFAULT '0',
  `mcuban` int(11) NOT NULL DEFAULT '0',
  `jfoxworthy` int(11) NOT NULL DEFAULT '0',
  `jpdejoria` int(11) NOT NULL DEFAULT '0',
  `stisch` int(11) NOT NULL DEFAULT '0',
  `nwoodman` int(11) NOT NULL DEFAULT '0',
  `other_terms` varchar(255) NOT NULL DEFAULT '',
  `admin_notes` varchar(255) NOT NULL DEFAULT '',
  `source1` varchar(255) NOT NULL DEFAULT '',
  `source2` varchar(255) NOT NULL DEFAULT '',
  `source3` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`DID`),
  KEY `COID` (`COID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `episodes`
--

CREATE TABLE IF NOT EXISTS `episodes` (
  `EPID` int(11) NOT NULL,
  `season` int(11) NOT NULL,
  `epnumber` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `airdate` date NOT NULL,
  `kharrington` tinyint(1) NOT NULL DEFAULT '0',
  `jfoxworthy` tinyint(1) NOT NULL DEFAULT '0',
  `rherjavec` tinyint(1) NOT NULL DEFAULT '0',
  `koleary` tinyint(1) NOT NULL DEFAULT '0',
  `bcorcoran` tinyint(1) NOT NULL DEFAULT '0',
  `djohn` tinyint(1) NOT NULL DEFAULT '0',
  `mcuban` tinyint(1) NOT NULL DEFAULT '0',
  `lgreiner` tinyint(1) NOT NULL DEFAULT '0',
  `stisch` tinyint(1) NOT NULL DEFAULT '0',
  `jpdejoria` tinyint(1) NOT NULL DEFAULT '0',
  `nwoodman` tinyint(4) NOT NULL DEFAULT '0',
  UNIQUE KEY `EPID` (`EPID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `pitches`
--

CREATE TABLE IF NOT EXISTS `pitches` (
  `PID` varchar(255) NOT NULL,
  `COID` varchar(255) NOT NULL,
  `EPID` varchar(255) NOT NULL,
  `deal` tinyint(1) NOT NULL,
  `ask_usd` int(11) NOT NULL,
  `ask_pct` float NOT NULL,
  `special` varchar(255) NOT NULL,
  PRIMARY KEY (`PID`),
  UNIQUE KEY `PID` (`PID`),
  KEY `COID` (`COID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `proposededits`
--

CREATE TABLE IF NOT EXISTS `proposededits` (
  `EID` int(11) NOT NULL AUTO_INCREMENT,
  `submitted` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approved` tinyint(1) NOT NULL DEFAULT '0',
  `type` varchar(255) NOT NULL,
  `changes` text NOT NULL,
  PRIMARY KEY (`EID`),
  UNIQUE KEY `EID` (`EID`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 AUTO_INCREMENT=21 ;

-- --------------------------------------------------------

--
-- Table structure for table `signuplist`
--

CREATE TABLE IF NOT EXISTS `signuplist` (
  `email` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
