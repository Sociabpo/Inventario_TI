-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: inventario_ti
-- ------------------------------------------------------
-- Server version	8.0.40

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `accesorios`
--

DROP TABLE IF EXISTS `accesorios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accesorios` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_placa_accesorio` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_usuario` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_accesorio` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `marca` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `modelo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `ubicacion` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_limite_devolucion` date DEFAULT NULL,
  `es_prestamo` tinyint(1) NOT NULL DEFAULT '0',
  `alerta_vencimiento_enviada` tinyint(1) NOT NULL DEFAULT '0',
  `garantia_meses` int DEFAULT NULL,
  `garantia_fin` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  KEY `id_usuario` (`id_usuario`),
  CONSTRAINT `accesorios_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `accesorios_ibfk_2` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accesorios`
--

LOCK TABLES `accesorios` WRITE;
/*!40000 ALTER TABLE `accesorios` DISABLE KEYS */;
INSERT INTO `accesorios` VALUES ('2be4ab50-60ec-4ba0-8c96-1096d1d0f83d','SCA0002','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Combo Tecl+Mou','Logitech','Silent','SEHJSERH','disponible',NULL,'2026-06-22 14:23:26','2026-06-22 14:23:26','CT',NULL,0,0,NULL,NULL),('86c964a2-7cc4-41f2-8cb6-f6f7e904e727','SCA0004','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Combo Tecl+Mou','Logitech','Combo teclado y mouse logitec','sazghytjv','disponible',NULL,'2026-06-22 16:41:27','2026-06-22 16:41:27','CT',NULL,0,0,NULL,NULL),('b4d487a5-ea00-4615-a4eb-d51729659365','SCA0001','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Combo','Logitech','Silent','sgfdgsdg','disponible',NULL,'2026-06-22 12:47:08','2026-06-22 12:47:08',NULL,NULL,0,0,NULL,NULL),('b74360f1-43a0-4afa-bb9b-1df3b166f8a3','SCA0005','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Combo Tecl+Mou','Logitech','Silent','nnmfdytjk','disponible',NULL,'2026-06-22 16:42:08','2026-06-22 16:42:08','CT',NULL,0,0,NULL,NULL),('bfad7466-a71f-4500-a7c4-a69c737f39e2','SCA0003','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Combo Tecl+Mou','Logitech','Silent','sdgaerh','disponible',NULL,'2026-06-22 16:40:53','2026-06-22 16:40:53','CT',NULL,0,0,NULL,NULL);
/*!40000 ALTER TABLE `accesorios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `acta_detalle`
--

DROP TABLE IF EXISTS `acta_detalle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `acta_detalle` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acta_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_item` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_activo` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_accesorio` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observacion` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `acta_id` (`acta_id`),
  KEY `id_activo` (`id_activo`),
  KEY `id_accesorio` (`id_accesorio`),
  CONSTRAINT `acta_detalle_ibfk_1` FOREIGN KEY (`acta_id`) REFERENCES `actas_entrega` (`id`),
  CONSTRAINT `acta_detalle_ibfk_2` FOREIGN KEY (`id_activo`) REFERENCES `activos` (`id`),
  CONSTRAINT `acta_detalle_ibfk_3` FOREIGN KEY (`id_accesorio`) REFERENCES `accesorios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `acta_detalle`
--

LOCK TABLES `acta_detalle` WRITE;
/*!40000 ALTER TABLE `acta_detalle` DISABLE KEYS */;
/*!40000 ALTER TABLE `acta_detalle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `actas_entrega`
--

DROP TABLE IF EXISTS `actas_entrega`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `actas_entrega` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_activo` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_usuario` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_entrega` datetime DEFAULT CURRENT_TIMESTAMP,
  `responsable_entrega` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `responsable_recibe` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `url_pdf` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hash_pdf` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `firmada` tinyint(1) NOT NULL DEFAULT '0',
  `fecha_firma` datetime DEFAULT NULL,
  `fecha_inicio_vigencia` date DEFAULT NULL,
  `es_anticipada` tinyint(1) NOT NULL DEFAULT '0',
  `recordatorios_enviados` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  KEY `id_activo` (`id_activo`),
  KEY `id_usuario` (`id_usuario`),
  CONSTRAINT `actas_entrega_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `actas_entrega_ibfk_2` FOREIGN KEY (`id_activo`) REFERENCES `activos` (`id`),
  CONSTRAINT `actas_entrega_ibfk_3` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `actas_entrega`
--

LOCK TABLES `actas_entrega` WRITE;
/*!40000 ALTER TABLE `actas_entrega` DISABLE KEYS */;
/*!40000 ALTER TABLE `actas_entrega` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `activos`
--

DROP TABLE IF EXISTS `activos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `activos` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_placa_activo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_usuario` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_activo` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `marca` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `modelo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `numero_parte` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `procesador` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `memoria_ram` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disco_1` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disco_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_compra` date DEFAULT NULL,
  `fecha_obsolescencia` date DEFAULT NULL,
  `costo` decimal(12,2) DEFAULT NULL,
  `estado` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `resolucion` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_conexion` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tamano_pantalla` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imei` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `numero_telefono` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `capacidad_almacenamiento` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `color` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_impresora` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ip_dispositivo` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_camara` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `canales_dvr` int DEFAULT NULL,
  `con_microfono` tinyint(1) DEFAULT NULL,
  `extension` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linea_telefono` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_telefono` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `capacidad_ups` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tiempo_respaldo_ups` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `codigo_contable` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ubicacion` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_limite_devolucion` date DEFAULT NULL,
  `es_prestamo` tinyint(1) NOT NULL DEFAULT '0',
  `alerta_vencimiento_enviada` tinyint(1) NOT NULL DEFAULT '0',
  `garantia_meses` int DEFAULT NULL,
  `garantia_fin` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  KEY `id_usuario` (`id_usuario`),
  CONSTRAINT `activos_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `activos_ibfk_2` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activos`
--

LOCK TABLES `activos` WRITE;
/*!40000 ALTER TABLE `activos` DISABLE KEYS */;
INSERT INTO `activos` VALUES ('11ba3b1b-4db3-4215-86db-e125e9cb8945','SC0001','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','HP','HP ProBook 445 G10','REGHAWEG',NULL,' i5-1135G7','16 GB DDR4',NULL,NULL,'2026-06-01','2031-06-01',4000000.00,'disponible',NULL,'2026-06-22 12:19:20','2026-06-22 17:08:28',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'Sede SC',NULL,0,0,NULL,NULL),('137b717e-f6fe-4953-8580-bcea57455301','SC0007','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','Dell','Dell inspiron C456','kmfyukffg',NULL,' i5-1135G7','16 GB DDR4','512 GB SSD NVMe',NULL,'2026-06-22','2031-06-22',NULL,'disponible',NULL,'2026-06-22 17:02:41','2026-06-22 17:02:41',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'CT',NULL,0,0,NULL,NULL),('1f6af8e6-1fc3-45d5-94d2-a9f66c7d8ab3','SC0006','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','HP','Hp probook 445 G10','sdghjukuym',NULL,' i7-1135G7','16 GB DDR4','512 GB SSD NVMe',NULL,'2026-06-22','2031-06-22',4500000.00,'disponible',NULL,'2026-06-22 16:44:31','2026-06-22 16:44:31',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'CT',NULL,0,0,NULL,NULL),('2c07ea7d-9850-40b4-b071-8eeb992090ed','SC0005','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','HP','Hp probook 445 G10','sedgserhsd',NULL,' i5-1135G7','16 GB DDR4','512 GB ','512 GB','2026-06-22','2031-06-22',4500000.00,'disponible',NULL,'2026-06-22 16:44:04','2026-06-22 16:44:04',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'CT',NULL,0,0,NULL,NULL),('8d98751f-229c-4856-a2b6-71d1ab1dafef','SC0003','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','HP','Hp probook 445 G10','dfsdgbvda',NULL,' i5-1135G7','16 GB DDR4','512 GB SSD NVMe',NULL,'2026-06-22','2031-06-22',4500000.00,'disponible',NULL,'2026-06-22 14:20:53','2026-06-22 14:20:53',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'Bodega CT',NULL,0,0,NULL,NULL),('cd210b4e-eefd-4b22-8b60-acaa53e40d51','SC0002','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','HP','Hp probook 445 G10','dfsdgbvda',NULL,' i5-1135G7','16 GB DDR4',NULL,NULL,'2026-06-22','2031-06-22',NULL,'disponible',NULL,'2026-06-22 12:47:08','2026-06-22 17:08:01',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'CT',NULL,0,0,NULL,NULL),('d7371cb3-6617-43b9-8fda-045bf96a9e14','SC0004','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',NULL,'Portatil','HP','Hp probook 445 G10','vcnsfsadfg',NULL,' i5-1135G7','32 GB DDR4','512 GB ',NULL,'2026-06-22','2031-06-22',4500000.00,'disponible',NULL,'2026-06-22 16:43:23','2026-06-22 16:43:23',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'CT',NULL,0,0,NULL,NULL);
/*!40000 ALTER TABLE `activos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ambientes`
--

DROP TABLE IF EXISTS `ambientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ambientes` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `color` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ambientes`
--

LOCK TABLES `ambientes` WRITE;
/*!40000 ALTER TABLE `ambientes` DISABLE KEYS */;
INSERT INTO `ambientes` VALUES ('2aadcdec-56d5-4a37-a3c1-b26478410cdb','Laboratorio','#27ae60'),('541dae44-f328-48b2-9e2c-cd9b243c2168','DR / Contingencia','#e67e22'),('6d54462b-b73d-4e9e-854e-62c0eb1d3b4c','Staging','#9b59b6'),('719c715b-ce03-4077-90df-4ea2bb8da6ed','Producción','#e74c3c'),('a96208c0-031d-43cc-9166-8fa10c2836de','Desarrollo','#3498db'),('fa6afaba-37d2-4940-b123-1e36eed1f4c0','QA / Pruebas','#f39c12');
/*!40000 ALTER TABLE `ambientes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `asignaciones`
--

DROP TABLE IF EXISTS `asignaciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `asignaciones` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_activo` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_usuario` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_asignacion` datetime DEFAULT CURRENT_TIMESTAMP,
  `fecha_devolucion` datetime DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asignado_por` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recibido_por` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  KEY `id_activo` (`id_activo`),
  KEY `id_usuario` (`id_usuario`),
  CONSTRAINT `asignaciones_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `asignaciones_ibfk_2` FOREIGN KEY (`id_activo`) REFERENCES `activos` (`id`),
  CONSTRAINT `asignaciones_ibfk_3` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `asignaciones`
--

LOCK TABLES `asignaciones` WRITE;
/*!40000 ALTER TABLE `asignaciones` DISABLE KEYS */;
/*!40000 ALTER TABLE `asignaciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_log`
--

DROP TABLE IF EXISTS `audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tabla` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operacion` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `registro_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `datos_anteriores` text COLLATE utf8mb4_unicode_ci,
  `datos_nuevos` text COLLATE utf8mb4_unicode_ci,
  `usuario_app` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ejecutado_en` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_log`
--

LOCK TABLES `audit_log` WRITE;
/*!40000 ALTER TABLE `audit_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `audit_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bajas_activos`
--

DROP TABLE IF EXISTS `bajas_activos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bajas_activos` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `numero_baja` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_recurso` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recurso_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `placa` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_activo` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `marca` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `modelo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_compra` date DEFAULT NULL,
  `costo_original` decimal(14,2) DEFAULT NULL,
  `motivo` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `justificacion` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado_fisico` text COLLATE utf8mb4_unicode_ci,
  `valor_venta` decimal(14,2) DEFAULT NULL,
  `comprador` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entidad_receptora` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metodo_destruccion` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado_aprobacion` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `solicitado_por_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aprobado_por_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_solicitud` datetime DEFAULT CURRENT_TIMESTAMP,
  `fecha_aprobacion` datetime DEFAULT NULL,
  `observaciones_aprobador` text COLLATE utf8mb4_unicode_ci,
  `url_pdf` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `numero_denuncia` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `empresa_destino_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `empresa_destino_nombre` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  CONSTRAINT `bajas_activos_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bajas_activos`
--

LOCK TABLES `bajas_activos` WRITE;
/*!40000 ALTER TABLE `bajas_activos` DISABLE KEYS */;
/*!40000 ALTER TABLE `bajas_activos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cambios_estado`
--

DROP TABLE IF EXISTS `cambios_estado`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cambios_estado` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_recurso` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recurso_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `placa` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado_anterior` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado_nuevo` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ubicacion` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_mantenimiento` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cubierto_garantia` tinyint(1) DEFAULT NULL,
  `cubre_garantia` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `garantia_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tiempo_estimado_dias` int DEFAULT NULL,
  `responsable_mant` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descripcion` text COLLATE utf8mb4_unicode_ci,
  `resultado_mant` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `costo_real` decimal(14,2) DEFAULT NULL,
  `genero_acta` tinyint(1) DEFAULT NULL,
  `acta_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `realizado_por_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha` datetime DEFAULT CURRENT_TIMESTAMP,
  `usuario_previo` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  CONSTRAINT `cambios_estado_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cambios_estado`
--

LOCK TABLES `cambios_estado` WRITE;
/*!40000 ALTER TABLE `cambios_estado` DISABLE KEYS */;
INSERT INTO `cambios_estado` VALUES ('1c85c0ea-f48e-491f-a116-34de457ee012','activo','11ba3b1b-4db3-4215-86db-e125e9cb8945','SC0001','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','disponible','disponible','Sede',NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,'1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22 12:20:13',NULL);
/*!40000 ALTER TABLE `cambios_estado` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `catalogos`
--

DROP TABLE IF EXISTS `catalogos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `catalogos` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `categoria` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `valor` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  `orden` int DEFAULT '0',
  `color` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `icono` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `anios_obsolescencia` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_catalogo_categoria_valor_empresa` (`categoria`,`valor`,`empresa_id`),
  KEY `empresa_id` (`empresa_id`),
  CONSTRAINT `catalogos_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `catalogos`
--

LOCK TABLES `catalogos` WRITE;
/*!40000 ALTER TABLE `catalogos` DISABLE KEYS */;
INSERT INTO `catalogos` VALUES ('01947e3b-dc0e-43a3-a1fa-38bd1832dd8b','tipo_mantenimiento','Preventivo',NULL,NULL,1,1,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('023cd0fd-1a31-4c58-ac31-d109ea763d1e','tipo_accesorio','Base portátil',NULL,NULL,1,11,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('042fd078-e3a9-4267-83ef-84c7453b791f','tipo_accesorio','Teclado',NULL,NULL,1,2,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('0d8a85de-dac1-4379-ba4a-f52b7afdbee9','tipo_activo','Portatil',NULL,NULL,1,11,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',5),('16486a88-a747-4cbb-bfed-19af5579fb92','tipo_mantenimiento','Limpieza',NULL,NULL,1,5,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('1cccc010-a40c-4470-9e9b-781d66198fe0','tipo_activo','Impresora',NULL,NULL,1,7,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',5),('26beafbf-289d-42b6-a993-a47225177549','cargo','Analista',NULL,'09a4a3d5-2286-45da-99e9-54c0f5de5a7a',1,1,NULL,NULL,'2026-06-05 08:42:11','2026-06-05 08:42:11',NULL),('2e4ba1df-cfe9-4e02-8513-589143ce4711','sede','Palacé',NULL,'09a4a3d5-2286-45da-99e9-54c0f5de5a7a',1,1,NULL,NULL,'2026-06-05 08:18:11','2026-06-05 08:18:11',NULL),('36c4551e-816f-4565-8527-4df5e286e936','tipo_activo','UPS',NULL,NULL,1,15,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',4),('401c6985-596e-44ec-af9e-b5fecab6d337','tipo_mantenimiento','Cambio de pieza',NULL,NULL,1,7,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('443fa447-f2f0-44a4-9c76-53ff4507cc4e','tipo_mantenimiento','Revisión técnica',NULL,NULL,1,8,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('478fb5e7-32db-45a8-93f3-e8ea26499906','tipo_proveedor','fabricante',NULL,NULL,1,3,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('48a89d5a-933a-4bfc-8aca-6e07466f2863','tipo_activo','PC',NULL,NULL,1,10,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 11:04:00',5),('62cd8aa7-1876-4e56-88a3-3c1be49d1b6f','tipo_activo','Escaner',NULL,NULL,1,6,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',6),('65667f05-bb15-43c1-9540-b7b209aa48c3','tipo_accesorio','Cable HDMI',NULL,NULL,1,7,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('65eb5ca1-b62d-4540-9bd3-6ae892cfbc5e','tipo_accesorio','Token USB',NULL,NULL,1,14,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('66d792eb-121b-4f8e-8707-1d8f3f242bde','tipo_activo','Camara',NULL,NULL,1,2,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',6),('6c900b4c-ab51-450b-b96a-9ef29eab35b8','tipo_mantenimiento','Garantía',NULL,NULL,1,4,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('729d8bdd-ba96-4310-87ff-a41a31d109fa','tipo_activo','AIO',NULL,NULL,1,1,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 11:10:09',5),('73bc38b1-8252-4c3d-b475-76df853b889b','tipo_accesorio','Base de Portatil',NULL,NULL,1,15,NULL,NULL,'2026-06-05 08:38:31','2026-06-05 08:38:31',NULL),('7539ec44-515d-4100-ac3a-a9acad0e04b9','tipo_activo','Celular',NULL,NULL,1,3,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',3),('82736293-31bd-4e6e-a06f-382e5d3da7a0','tipo_activo','Ipad',NULL,NULL,1,8,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',4),('8631451f-433d-4b6a-b092-b0618e57fb1c','tipo_activo','Tablet',NULL,NULL,1,12,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',4),('875f58ac-1ec1-4745-a96e-59a6a928f419','tipo_accesorio','Micrófono',NULL,NULL,1,10,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('8df23fb2-077c-4bb3-b15f-b2540e0b93d3','tipo_accesorio','Webcam',NULL,NULL,1,9,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('8fa838b6-42de-4c2a-988e-3d799e5b5c44','tipo_proveedor','arrendador',NULL,NULL,1,2,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('93c9ef29-f022-4317-a3d8-79592cc5a7b8','tipo_activo','Diadema',NULL,NULL,1,4,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',3),('9777a372-7134-489f-8116-4c4d61248b25','tipo_activo','Monitor',NULL,NULL,1,9,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',7),('9ef612a2-f72f-4d54-a891-9abe28a3d708','tipo_accesorio','Pad mouse',NULL,NULL,1,12,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('a1b70689-913e-477b-a02e-97c8f35547ea','tipo_mantenimiento','Predictivo',NULL,NULL,1,3,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('a88acd58-95ab-4c61-a8ed-45efe592036d','tipo_accesorio','Diadema',NULL,NULL,1,3,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('a94e78e5-8efc-40c8-9820-3a655f74f93d','tipo_accesorio','Cable USB',NULL,NULL,1,8,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('abe4e3fb-5667-4bc0-86f1-719acae12de9','tipo_activo','Video Beam',NULL,NULL,1,16,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',6),('abedf350-2fe8-4942-86a0-9ded0a332df0','tipo_accesorio','Bolso/Maletín',NULL,NULL,1,6,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('b8e7b071-eda5-4138-961b-8c40f1ddab15','tipo_mantenimiento','Actualización software',NULL,NULL,1,6,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('bf174381-0ebf-4e40-b117-c03e6b5bd3a1','tipo_activo','Televisor',NULL,NULL,1,14,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',7),('bf53a080-e292-418f-bb2d-fae911379254','tipo_proveedor','vendedor',NULL,NULL,1,1,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('c41703b6-2825-4f22-bb35-7a7f3a4ab5e2','tipo_activo','DVR',NULL,NULL,1,5,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',6),('d6d158ff-2d47-47a2-8da7-5b706420581d','tipo_accesorio','Lector huella',NULL,NULL,1,13,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('dc6268b0-5ee1-445d-8bb3-55b73e842325','tipo_mantenimiento','Correctivo',NULL,NULL,1,2,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('dd3d3f6b-5eb1-4631-9fbc-4b42afcd27a6','tipo_accesorio','Cargador',NULL,NULL,1,5,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('e1498ad3-e226-4c22-abc0-7b04e192dceb','area','Tecnología',NULL,'09a4a3d5-2286-45da-99e9-54c0f5de5a7a',1,1,NULL,NULL,'2026-06-05 08:41:57','2026-06-05 08:41:57',NULL),('ea34cd67-2b59-443c-a6de-5c7bef373ffd','tipo_activo','Telefono',NULL,NULL,1,13,NULL,NULL,'2026-06-04 20:39:04','2026-06-20 10:57:56',7),('f0136916-fb8b-407e-8614-fb367ed9f37c','tipo_accesorio','Hub USB',NULL,NULL,1,4,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL),('f78ffbde-4131-4d63-9f3d-a153d31c7a45','tipo_accesorio','Combo Tecl+Mou',NULL,NULL,1,16,NULL,NULL,'2026-06-22 14:22:14','2026-06-22 14:22:14',NULL),('fa097301-eed9-48b2-a998-22a37ccfec7d','tipo_accesorio','Mouse',NULL,NULL,1,1,NULL,NULL,'2026-06-04 20:39:04','2026-06-04 20:39:04',NULL);
/*!40000 ALTER TABLE `catalogos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `consecutivos`
--

DROP TABLE IF EXISTS `consecutivos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consecutivos` (
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ultimo_numero` int DEFAULT NULL,
  PRIMARY KEY (`empresa_id`,`tipo`),
  CONSTRAINT `consecutivos_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `consecutivos`
--

LOCK TABLES `consecutivos` WRITE;
/*!40000 ALTER TABLE `consecutivos` DISABLE KEYS */;
INSERT INTO `consecutivos` VALUES ('09a4a3d5-2286-45da-99e9-54c0f5de5a7a','ACCESORIO',5),('09a4a3d5-2286-45da-99e9-54c0f5de5a7a','ACTIVO',7),('3a7a8133-25a7-44ab-a345-70fa0b6d8f6b','ACCESORIO',0),('3a7a8133-25a7-44ab-a345-70fa0b6d8f6b','ACTIVO',0),('4676ae6d-5793-4630-8610-787c68005b49','ACCESORIO',0),('4676ae6d-5793-4630-8610-787c68005b49','ACTIVO',0);
/*!40000 ALTER TABLE `consecutivos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `contratos_alquiler`
--

DROP TABLE IF EXISTS `contratos_alquiler`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `contratos_alquiler` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `orden_compra_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `proveedor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `activo_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accesorio_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL,
  `valor_mensual` decimal(14,2) NOT NULL,
  `valor_total_contrato` decimal(14,2) DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_devolucion_real` date DEFAULT NULL,
  `observaciones_devolucion` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `orden_compra_id` (`orden_compra_id`),
  KEY `proveedor_id` (`proveedor_id`),
  KEY `activo_id` (`activo_id`),
  KEY `accesorio_id` (`accesorio_id`),
  KEY `ix_contratos_alquiler_estado` (`estado`),
  KEY `ix_contratos_alquiler_empresa_id` (`empresa_id`),
  CONSTRAINT `contratos_alquiler_ibfk_1` FOREIGN KEY (`orden_compra_id`) REFERENCES `ordenes_compra` (`id`),
  CONSTRAINT `contratos_alquiler_ibfk_2` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `contratos_alquiler_ibfk_3` FOREIGN KEY (`proveedor_id`) REFERENCES `proveedores` (`id`),
  CONSTRAINT `contratos_alquiler_ibfk_4` FOREIGN KEY (`activo_id`) REFERENCES `activos` (`id`),
  CONSTRAINT `contratos_alquiler_ibfk_5` FOREIGN KEY (`accesorio_id`) REFERENCES `accesorios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `contratos_alquiler`
--

LOCK TABLES `contratos_alquiler` WRITE;
/*!40000 ALTER TABLE `contratos_alquiler` DISABLE KEYS */;
/*!40000 ALTER TABLE `contratos_alquiler` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `criticidades`
--

DROP TABLE IF EXISTS `criticidades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `criticidades` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nivel` int NOT NULL,
  `color` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `criticidades`
--

LOCK TABLES `criticidades` WRITE;
/*!40000 ALTER TABLE `criticidades` DISABLE KEYS */;
INSERT INTO `criticidades` VALUES ('4301ff83-7383-4e48-9f9a-913c8caa6556','Crítico',4,'#c0392b'),('b1e919ad-bc6f-4e74-bec6-40a00f581a5f','Alto',3,'#e74c3c'),('e59f6fac-cfea-444b-b75e-ad5f944f9cf4','Bajo',1,'#27ae60'),('e9544258-8b99-42d1-8b38-9f1e361fcc47','Medio',2,'#f39c12');
/*!40000 ALTER TABLE `criticidades` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `empresa_relaciones`
--

DROP TABLE IF EXISTS `empresa_relaciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresa_relaciones` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_a_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_b_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_empresa_relacion` (`empresa_a_id`,`empresa_b_id`),
  KEY `ix_emp_rel_a` (`empresa_a_id`),
  KEY `ix_emp_rel_b` (`empresa_b_id`),
  CONSTRAINT `empresa_relaciones_ibfk_1` FOREIGN KEY (`empresa_a_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `empresa_relaciones_ibfk_2` FOREIGN KEY (`empresa_b_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empresa_relaciones`
--

LOCK TABLES `empresa_relaciones` WRITE;
/*!40000 ALTER TABLE `empresa_relaciones` DISABLE KEYS */;
INSERT INTO `empresa_relaciones` VALUES ('924fc79c-1543-415c-9919-d9f23c057d01','3a7a8133-25a7-44ab-a345-70fa0b6d8f6b','d68bd912-5d65-4548-a2a5-dbd197891028','2026-06-23 15:05:00');
/*!40000 ALTER TABLE `empresa_relaciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `empresas`
--

DROP TABLE IF EXISTS `empresas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresas` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nit` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre_empresa` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `prefijo` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'XX',
  `direccion` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ciudad` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `sedes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nit` (`nit`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empresas`
--

LOCK TABLES `empresas` WRITE;
/*!40000 ALTER TABLE `empresas` DISABLE KEYS */;
INSERT INTO `empresas` VALUES ('09a4a3d5-2286-45da-99e9-54c0f5de5a7a','900.562.737-5','Socia BPO','SC','CRA 50 #38- 35','Medellin',NULL,NULL,1,'2026-05-19 20:34:36','2026-05-20 10:10:01',NULL),('3a7a8133-25a7-44ab-a345-70fa0b6d8f6b','890904615','Autoamerica','AA','CRA 50 #38- 35','Medellin',NULL,NULL,1,'2026-05-24 10:53:05','2026-06-01 21:56:30','[\"Palac\\u00e9\", \"Envigado\", \"Apartad\\u00f3\", \"Llano Grande\"]'),('4676ae6d-5793-4630-8610-787c68005b49','901.606.278','Vocé Group S.A.S','VC','Cra 48 #19 sur - 100 Zona 2 Ed. Chelsea Ofi 707','Medellin',NULL,NULL,1,'2026-05-20 10:09:37','2026-05-20 10:09:37',NULL),('d68bd912-5d65-4548-a2a5-dbd197891028','900707055','Automax S.A.S','AX','Calle 12 sur #51-90','Medellin','4441160','info@automax.com.co',1,'2026-06-23 15:04:43','2026-06-23 15:05:00','[\"Aguacatala\", \"Pereira\", \"Bucaramanga\"]');
/*!40000 ALTER TABLE `empresas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `estados_servidor`
--

DROP TABLE IF EXISTS `estados_servidor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `estados_servidor` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `color` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `estados_servidor`
--

LOCK TABLES `estados_servidor` WRITE;
/*!40000 ALTER TABLE `estados_servidor` DISABLE KEYS */;
INSERT INTO `estados_servidor` VALUES ('20351530-0910-496a-a0a0-ea487e9453a0','Inactivo','#95a5a6'),('71095bfe-d7c4-4cb1-97f3-afca6029d6c2','Activo','#27ae60'),('75f9f6ae-cfed-4d5a-9f9e-9569f44c792d','En instalación','#3498db'),('7e5a4e1a-c6b9-4bd9-9dcd-c2403f30c554','En mantenimiento','#f39c12'),('8f4e33bb-9fdb-4137-b14b-c16b2096f2ec','Dado de baja','#7f8c8d');
/*!40000 ALTER TABLE `estados_servidor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `facturas`
--

DROP TABLE IF EXISTS `facturas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `facturas` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `orden_compra_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `proveedor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `numero_factura` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_factura` date NOT NULL,
  `fecha_vencimiento` date DEFAULT NULL,
  `subtotal` decimal(14,2) DEFAULT NULL,
  `iva` decimal(14,2) DEFAULT NULL,
  `valor_total` decimal(14,2) NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `url_pdf` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `proveedor_id` (`proveedor_id`),
  KEY `ix_facturas_orden_compra_id` (`orden_compra_id`),
  KEY `ix_facturas_estado` (`estado`),
  KEY `ix_facturas_empresa_id` (`empresa_id`),
  CONSTRAINT `facturas_ibfk_1` FOREIGN KEY (`orden_compra_id`) REFERENCES `ordenes_compra` (`id`),
  CONSTRAINT `facturas_ibfk_2` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `facturas_ibfk_3` FOREIGN KEY (`proveedor_id`) REFERENCES `proveedores` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `facturas`
--

LOCK TABLES `facturas` WRITE;
/*!40000 ALTER TABLE `facturas` DISABLE KEYS */;
/*!40000 ALTER TABLE `facturas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `firma_tokens`
--

DROP TABLE IF EXISTS `firma_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `firma_tokens` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acta_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `usado` tinyint(1) DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `ip_firmante` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `firma_base64` text COLLATE utf8mb4_unicode_ci,
  `firmado_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `nombre_firmante` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entrega_por_tercero` tinyint(1) NOT NULL DEFAULT '0',
  `nombre_tercero` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relacion_tercero` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones_firma` text COLLATE utf8mb4_unicode_ci,
  `correo_movil` tinyint(1) DEFAULT NULL,
  `otp_verificado` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `acta_id` (`acta_id`),
  CONSTRAINT `firma_tokens_ibfk_1` FOREIGN KEY (`acta_id`) REFERENCES `actas_entrega` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `firma_tokens`
--

LOCK TABLES `firma_tokens` WRITE;
/*!40000 ALTER TABLE `firma_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `firma_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `garantias`
--

DROP TABLE IF EXISTS `garantias`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `garantias` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `activo_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accesorio_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `factura_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `proveedor_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `numero_garantia` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL,
  `condiciones` text COLLATE utf8mb4_unicode_ci,
  `url_documento` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `activo_id` (`activo_id`),
  KEY `accesorio_id` (`accesorio_id`),
  KEY `factura_id` (`factura_id`),
  KEY `proveedor_id` (`proveedor_id`),
  KEY `ix_garantias_empresa_id` (`empresa_id`),
  KEY `ix_garantias_estado` (`estado`),
  CONSTRAINT `garantias_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `garantias_ibfk_2` FOREIGN KEY (`activo_id`) REFERENCES `activos` (`id`),
  CONSTRAINT `garantias_ibfk_3` FOREIGN KEY (`accesorio_id`) REFERENCES `accesorios` (`id`),
  CONSTRAINT `garantias_ibfk_4` FOREIGN KEY (`factura_id`) REFERENCES `facturas` (`id`),
  CONSTRAINT `garantias_ibfk_5` FOREIGN KEY (`proveedor_id`) REFERENCES `proveedores` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `garantias`
--

LOCK TABLES `garantias` WRITE;
/*!40000 ALTER TABLE `garantias` DISABLE KEYS */;
/*!40000 ALTER TABLE `garantias` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `herramientas`
--

DROP TABLE IF EXISTS `herramientas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `herramientas` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `categoria` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `herramientas`
--

LOCK TABLES `herramientas` WRITE;
/*!40000 ALTER TABLE `herramientas` DISABLE KEYS */;
INSERT INTO `herramientas` VALUES ('04ba2ef7-8e99-4ab7-8ba3-cfe9886dd9f5','Puppet','Gestión de Configuración','Automatización de configuración',0),('1470add2-2e79-4418-997b-f551bc50c653','Qualys VMDR','Vulnerabilidades','Gestión de vulnerabilidades',0),('19e0b855-7515-48b4-a3d4-0e33fd8fb499','Atera','RMM','Plataforma RMM de monitoreo y gestión remota',1),('1a247c0c-6bf6-4da7-b17f-aed4bf7bec97','New Relic','APM','Observabilidad de aplicaciones',0),('25a6e88e-e0c1-4f54-8c44-b46d6a1bd42f','Nagios','Monitoreo','Monitoreo de servicios y hosts',0),('2e475ff1-2dd3-4585-ad13-93354bd4f47b','Commvault','Backup','Plataforma de protección de datos',0),('3cf89002-aa71-41fb-b7a8-037ec9d87c80','Backup Exec','Backup','Solución de backup Veritas',0),('50a77bbd-0676-4028-a762-e45bde0d7847','Forticlient','EDR/AV','Endpoint security y VPN de Fortinet',1),('51ccba01-d849-43ed-a59d-de58467bdcd0','SentinelOne','EDR/AV','Plataforma EDR con IA',0),('5567cdf1-1c77-4cf2-9edf-a0e711fc4358','Datadog','APM','Plataforma de observabilidad',0),('56f9be8d-be4f-402b-afb5-4f08d9256643','Grafana','Monitoreo','Visualización de métricas y dashboards',0),('582810f1-f20f-4e89-ba04-9084c38b59a5','Wazuh','SIEM','SIEM open source, XDR y detección de amenazas',1),('7236fb8f-6361-43e1-963b-b675d563fc3d','IBM QRadar','SIEM','Plataforma SIEM empresarial',0),('78cc6b9d-3923-4bc5-b1cd-31c4b4aaa5f5','EDR','EDR/AV','Solución de detección y respuesta en endpoints',1),('7bfd624d-ecee-4235-8691-7e622fee7d29','SolarWinds','Monitoreo','Monitoreo de redes e infraestructura',0),('80360b75-5ee7-4b1c-95d4-92f132c91e52','Trend Micro Deep Security','EDR/AV','Seguridad de servidores',0),('8ad341cc-d3c8-490b-9d4b-eeb077ef3209','Elastic SIEM','SIEM','SIEM basado en Elastic Stack',0),('b1528aed-5524-4919-8000-5bf2e0b2a5c6','Splunk','SIEM','Plataforma SIEM y análisis de logs',0),('b4180e2a-1a84-4b0d-8cf6-c6d8d995d6b9','Veeam','Backup','Backup y recuperación',0),('b41aaae0-7598-4154-9e25-3b0b5dab2c69','Zabbix','Monitoreo','Monitoreo de infraestructura, métricas y alertas',1),('c2ff70ce-6eeb-494d-a745-1347d9fdadb8','OpenVAS','Vulnerabilidades','Escáner open source',0),('caffc10d-fc03-4c80-92d4-f2a513f5dcd7','Dynatrace','APM','Monitoreo de rendimiento de aplicaciones',0),('ce59c3f8-c0b8-4fec-9bd6-fadea2c42af4','Chef','Gestión de Configuración','Gestión de configuración',0),('e48bc929-2a6f-42bf-af8a-10e50a380740','Carbon Black','EDR/AV','Protección de endpoints',0),('e5d03a1c-7fa0-4c10-80e6-47a002c21f06','Bitdefender','EDR/AV','Plataforma de seguridad y protección avanzada',1),('f089c732-c000-4af8-a74d-627be62c811f','CrowdStrike Falcon','EDR/AV','Plataforma EDR en la nube',0),('f13cffa5-21c5-44a1-8982-882bab356e85','Tenable Nessus','Vulnerabilidades','Escáner de vulnerabilidades',0),('f3aca3cd-a1de-4a53-829b-94b65469a05d','Rapid7 InsightVM','Vulnerabilidades','Gestión de vulnerabilidades',0),('fa8adb13-d7e2-421f-87f0-fd7d37a4fb43','Prometheus','Monitoreo','Sistema de monitoreo y alertas',0),('fd8819bd-605c-4a91-8607-6700afcd97f6','Ansible','Gestión de Configuración','Automatización y orquestación',0);
/*!40000 ALTER TABLE `herramientas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `historial_movimientos`
--

DROP TABLE IF EXISTS `historial_movimientos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `historial_movimientos` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_activo` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_accesorio` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_usuario` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_acta` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_movimiento` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_movimiento` datetime DEFAULT CURRENT_TIMESTAMP,
  `responsable` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `id_activo` (`id_activo`),
  KEY `id_accesorio` (`id_accesorio`),
  KEY `id_usuario` (`id_usuario`),
  KEY `id_acta` (`id_acta`),
  CONSTRAINT `historial_movimientos_ibfk_1` FOREIGN KEY (`id_activo`) REFERENCES `activos` (`id`),
  CONSTRAINT `historial_movimientos_ibfk_2` FOREIGN KEY (`id_accesorio`) REFERENCES `accesorios` (`id`),
  CONSTRAINT `historial_movimientos_ibfk_3` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `historial_movimientos_ibfk_4` FOREIGN KEY (`id_acta`) REFERENCES `actas_entrega` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `historial_movimientos`
--

LOCK TABLES `historial_movimientos` WRITE;
/*!40000 ALTER TABLE `historial_movimientos` DISABLE KEYS */;
INSERT INTO `historial_movimientos` VALUES ('14fa78f5-f378-452f-8436-55550b64203b',NULL,NULL,NULL,NULL,'creacion','2026-06-22 17:02:41','ricardo.tamayo@sociabpo.com','Activo SC0007 registrado en el sistema'),('18c1a6a0-6923-4b3b-a2be-45ddec1cdda8','8d98751f-229c-4856-a2b6-71d1ab1dafef',NULL,NULL,NULL,'creacion','2026-06-22 14:20:53','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 12354'),('3624c45b-c8a6-4b5c-a90a-02644a913b7a',NULL,NULL,NULL,NULL,'creacion','2026-06-22 16:42:08','ricardo.tamayo@sociabpo.com','Accesorio SCA0005 registrado en el sistema'),('46253d47-59b3-4187-9a37-08941bd759ba',NULL,NULL,NULL,NULL,'creacion','2026-06-22 16:44:31','ricardo.tamayo@sociabpo.com','Activo SC0006 registrado en el sistema'),('577c0d94-94b9-4f61-9b0c-7751c5176f92',NULL,'bfad7466-a71f-4500-a7c4-a69c737f39e2',NULL,NULL,'creacion','2026-06-22 16:40:53','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123475'),('61c886d6-bea2-4e0e-9687-db73104bae0e',NULL,NULL,NULL,NULL,'creacion','2026-06-22 16:41:27','ricardo.tamayo@sociabpo.com','Accesorio SCA0004 registrado en el sistema'),('62973a94-74a6-4920-8f28-c8a8d5581e52',NULL,NULL,NULL,NULL,'creacion','2026-06-22 14:23:26','ricardo.tamayo@sociabpo.com','Accesorio SCA0002 registrado en el sistema'),('6dccb13e-367b-4f89-a3e1-73a4ee9c153b','d7371cb3-6617-43b9-8fda-045bf96a9e14',NULL,NULL,NULL,'creacion','2026-06-22 16:43:23','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123475'),('745770c5-4ad9-4153-9705-59981ec6788b',NULL,'2be4ab50-60ec-4ba0-8c96-1096d1d0f83d',NULL,NULL,'creacion','2026-06-22 14:23:26','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 12354'),('7546bb3b-056f-4f08-abe7-00f80cd51c52',NULL,NULL,NULL,NULL,'creacion','2026-06-22 16:40:53','ricardo.tamayo@sociabpo.com','Accesorio SCA0003 registrado en el sistema'),('7adee0fe-bc79-4f6a-b97a-e10d0c8eb453','11ba3b1b-4db3-4215-86db-e125e9cb8945',NULL,NULL,NULL,'cambio_estado','2026-06-22 12:20:13','Ricardo Tamayo','Estado: disponible → disponible · Sede'),('7dd91148-c9f3-4036-bd1b-37bfbb4f1d50','1f6af8e6-1fc3-45d5-94d2-a9f66c7d8ab3',NULL,NULL,NULL,'creacion','2026-06-22 16:44:31','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123475'),('8c0cb49a-c89a-42ea-99f3-e268fd0a7b25','2c07ea7d-9850-40b4-b071-8eeb992090ed',NULL,NULL,NULL,'creacion','2026-06-22 16:44:04','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123475'),('96f9e7f3-eded-4a33-94e2-f62297896099',NULL,'b74360f1-43a0-4afa-bb9b-1df3b166f8a3',NULL,NULL,'creacion','2026-06-22 16:42:08','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123475'),('9c63270f-a22d-41ab-840d-885788645411',NULL,NULL,NULL,NULL,'creacion','2026-06-22 12:19:20','ricardo.tamayo@sociabpo.com','Activo SC0001 registrado en el sistema'),('a7dfedd2-b2c2-4f54-8943-345cca890d91',NULL,NULL,NULL,NULL,'creacion','2026-06-22 16:43:23','ricardo.tamayo@sociabpo.com','Activo SC0004 registrado en el sistema'),('b6f2d60c-3338-4e6a-8506-e965859b8e23','137b717e-f6fe-4953-8580-bcea57455301',NULL,NULL,NULL,'creacion','2026-06-22 17:02:41','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123472345'),('d896b793-5802-475d-99d9-4e5490349062',NULL,'86c964a2-7cc4-41f2-8cb6-f6f7e904e727',NULL,NULL,'creacion','2026-06-22 16:41:27','ricardo.tamayo@sociabpo.com','Creado desde recepción OC 123475'),('e9ad6998-9809-4302-bbe4-1f772f2fe0b7',NULL,NULL,NULL,NULL,'creacion','2026-06-22 16:44:04','ricardo.tamayo@sociabpo.com','Activo SC0005 registrado en el sistema'),('fb4a1fe0-8ed9-40ee-bc62-0e4c29dcdb30',NULL,NULL,NULL,NULL,'creacion','2026-06-22 14:20:53','ricardo.tamayo@sociabpo.com','Activo SC0003 registrado en el sistema');
/*!40000 ALTER TABLE `historial_movimientos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `historial_servidores`
--

DROP TABLE IF EXISTS `historial_servidores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `historial_servidores` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `servidor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `usuario_sistema_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_cambio` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `campo_modificado` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valor_anterior` text COLLATE utf8mb4_unicode_ci,
  `valor_nuevo` text COLLATE utf8mb4_unicode_ci,
  `observacion` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `servidor_id` (`servidor_id`),
  KEY `usuario_sistema_id` (`usuario_sistema_id`),
  CONSTRAINT `historial_servidores_ibfk_1` FOREIGN KEY (`servidor_id`) REFERENCES `servidores` (`id`),
  CONSTRAINT `historial_servidores_ibfk_2` FOREIGN KEY (`usuario_sistema_id`) REFERENCES `usuarios_sistema` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `historial_servidores`
--

LOCK TABLES `historial_servidores` WRITE;
/*!40000 ALTER TABLE `historial_servidores` DISABLE KEYS */;
INSERT INTO `historial_servidores` VALUES ('0a50589b-2371-483b-a145-45f1c7288037','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','edicion','observaciones',NULL,'Test observacion verificacion',NULL,'2026-05-25 12:48:15'),('0b55e51e-de53-4167-a8a1-7dfcee0c74f1','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','edicion','so_id',NULL,'112b852e-a769-47a0-b440-3155c83cafe1',NULL,'2026-05-26 07:40:43'),('196ea8d0-b807-4c0a-a898-ca38b420d5ed','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','edicion','tipo_servidor_id','9a6d7699-1eff-4906-acae-dd764b6f938b','f44c058c-ee01-451c-9b49-7a935a193eed',NULL,'2026-05-26 07:40:43'),('225d4195-41e7-40cf-b469-da54ee109d35','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','edicion','ambiente_id','a96208c0-031d-43cc-9166-8fa10c2836de','719c715b-ce03-4077-90df-4ea2bb8da6ed',NULL,'2026-05-26 07:40:43'),('3467b53f-8786-46bb-854c-312dd48c650a','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','herramienta_asignada',NULL,NULL,NULL,'Herramienta \'Datadog\' asignada','2026-05-25 12:48:15'),('388dacbd-5f20-4aff-9346-2fa000c76c4d','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','edicion','criticidad_id',NULL,'e9544258-8b99-42d1-8b38-9f1e361fcc47',NULL,'2026-05-26 07:40:43'),('45a3b96e-6ed8-49de-b547-1c13bfb5e7b5','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','herramienta_removida',NULL,NULL,NULL,'Herramienta \'Datadog\' removida','2026-05-25 12:48:15'),('4964841b-ef83-4b7d-9eae-8daf4eba96a8','ff0a6654-dfed-4443-818d-412d00aa5bf6','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','herramienta_asignada',NULL,NULL,NULL,'Herramienta \'Zabbix\' asignada','2026-05-29 08:24:27'),('63481711-491f-45a6-890d-70f499d0d1f9','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','creacion',NULL,NULL,NULL,'Servidor srv-test-verif-01.local registrado','2026-05-25 12:48:15'),('6902de6d-4b68-48be-abba-8b1f2c021d07','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','edicion','disco',NULL,'500GB',NULL,'2026-05-26 07:40:43'),('802d943c-3dd6-41e8-9a12-18b3c7f1bcf6','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','herramienta_asignada',NULL,NULL,NULL,'Herramienta \'Atera\' asignada','2026-05-29 08:53:35'),('dee3558b-ae28-4edd-8dc8-d676dafeec51','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','herramienta_asignada',NULL,NULL,NULL,'Herramienta \'Forticlient\' asignada','2026-05-29 08:52:30'),('f22b719b-dc7a-4470-b530-6eed9421cae4','05417c82-46b3-47d3-93e4-ff762490e028','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','baja',NULL,NULL,NULL,'Servidor desactivado','2026-05-25 12:48:16');
/*!40000 ALTER TABLE `historial_servidores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ordenes_compra`
--

DROP TABLE IF EXISTS `ordenes_compra`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ordenes_compra` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `solicitud_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `proveedor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `numero_oc` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_emision` date NOT NULL,
  `fecha_entrega_esperada` date DEFAULT NULL,
  `valor_total` decimal(14,2) DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `fecha_inicio_alquiler` date DEFAULT NULL,
  `fecha_fin_alquiler` date DEFAULT NULL,
  `valor_mensual_alquiler` decimal(14,2) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `proveedor_id` (`proveedor_id`),
  KEY `ix_ordenes_compra_empresa_id` (`empresa_id`),
  KEY `ix_ordenes_compra_solicitud_id` (`solicitud_id`),
  KEY `ix_ordenes_compra_estado` (`estado`),
  CONSTRAINT `ordenes_compra_ibfk_1` FOREIGN KEY (`solicitud_id`) REFERENCES `solicitudes_compra` (`id`),
  CONSTRAINT `ordenes_compra_ibfk_2` FOREIGN KEY (`proveedor_id`) REFERENCES `proveedores` (`id`),
  CONSTRAINT `ordenes_compra_ibfk_3` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ordenes_compra`
--

LOCK TABLES `ordenes_compra` WRITE;
/*!40000 ALTER TABLE `ordenes_compra` DISABLE KEYS */;
INSERT INTO `ordenes_compra` VALUES ('618afaf9-7bf0-45a5-afab-a5fdd700e4c1','881d9db2-cc0b-4e82-8b9e-516d8a8dec79','ca84161f-9a3e-4cbe-a57d-969a95a4be2f','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','12354','compra','2026-06-22','2026-06-29',4650000.00,'recibida',NULL,NULL,NULL,NULL,'2026-06-22 12:41:21','2026-06-22 12:45:19'),('713aa0b4-6d06-47da-ba35-0b5db5e10557','acae5078-31fe-4593-91de-60faa3c17d0b','ca84161f-9a3e-4cbe-a57d-969a95a4be2f','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','123475','compra','2026-06-22','2026-06-29',13950000.00,'recibida',NULL,NULL,NULL,NULL,'2026-06-22 14:54:24','2026-06-22 14:55:27'),('e163b247-73fb-4e0a-b56a-cedb7df293be','a4ca60fd-17b7-42ea-b9f7-7591f70a0946','ca84161f-9a3e-4cbe-a57d-969a95a4be2f','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','123472345','alquiler','2026-06-22','2026-06-22',NULL,'recibida',NULL,'2026-06-22','2026-06-24',50000.00,'2026-06-22 17:01:13','2026-06-22 17:01:34');
/*!40000 ALTER TABLE `ordenes_compra` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `otp_tokens`
--

DROP TABLE IF EXISTS `otp_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `otp_tokens` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `firma_token_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `codigo` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `usado` tinyint(1) DEFAULT NULL,
  `verificado` tinyint(1) DEFAULT NULL,
  `intentos_fallidos` int DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `firma_token_id` (`firma_token_id`),
  CONSTRAINT `otp_tokens_ibfk_1` FOREIGN KEY (`firma_token_id`) REFERENCES `firma_tokens` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `otp_tokens`
--

LOCK TABLES `otp_tokens` WRITE;
/*!40000 ALTER TABLE `otp_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `otp_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `permisos`
--

DROP TABLE IF EXISTS `permisos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `permisos` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `codigo` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `modulo` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `accion` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `permisos`
--

LOCK TABLES `permisos` WRITE;
/*!40000 ALTER TABLE `permisos` DISABLE KEYS */;
INSERT INTO `permisos` VALUES ('0084505b-3d58-4116-aa1d-391841126291','activos.asignar','Asignar activos a empleados','activos','asignar','2026-05-24 09:17:53'),('051dd8c6-1ae3-4b99-94b1-8025834cc930','accesorios.asignar','Asignar accesorios a empleados','accesorios','asignar','2026-05-24 09:17:53'),('092130d7-4b99-4617-b219-d11bed979fce','reportes.exportar','Exportar reportes','reportes','exportar','2026-05-24 09:17:53'),('09fe697d-2dd8-40db-a236-5335651344e4','compras.crear_inventario','Crear activos/accesorios desde recepciones','compras','crear_inventario','2026-06-01 23:36:06'),('13110d43-63ec-4b35-a9c4-52104a7d2e01','empresas.ver','Ver empresas','empresas','ver','2026-05-24 09:17:53'),('1a345a68-593c-46b9-abd5-4ef4bc73f4a1','auditoria.ver','Ver log de auditoría','auditoria','ver','2026-05-24 09:17:53'),('212e9312-3860-43ae-8ee1-40d2a1bc1219','empresas.crear','Crear empresas','empresas','crear','2026-05-24 09:17:53'),('217f218f-076a-4aee-b42a-e80527d11ad3','accesorios.eliminar','Eliminar accesorios','accesorios','eliminar','2026-05-24 09:17:53'),('253e3798-8557-4b8c-913e-c09675c870f7','usuarios.eliminar','Eliminar empleados','usuarios','eliminar','2026-05-24 09:17:53'),('299e8df4-ca25-4948-824f-92a08a744692','activos.ver','Ver listado de activos','activos','ver','2026-05-24 09:17:53'),('32801561-71df-4e26-a890-4da91f85489b','asignaciones.devolver','Procesar devoluciones','asignaciones','devolver','2026-05-24 09:17:53'),('34165deb-1f8f-4645-8c46-de403d62f5b6','catalogos.ver','Ver catálogos / listas desplegables','catalogos','ver','2026-06-04 20:39:04'),('349eaaf6-5379-4473-aafa-de53b50a9825','actas.descargar','Descargar actas PDF','actas','descargar','2026-05-24 09:17:53'),('36ec0020-535f-4dfb-9a6b-972130d195e9','servidores.ver','Ver listado e información de servidores','servidores','ver','2026-05-25 11:58:22'),('41e864f5-a4a7-4328-8612-362c4a995662','activos.crear','Crear nuevos activos','activos','crear','2026-05-24 09:17:53'),('43c8e1c5-a245-48ff-9460-78920a3dea9c','servidores.crear','Registrar nuevos servidores','servidores','crear','2026-05-25 11:58:22'),('458b0ac6-0196-4576-a3de-15ebb353809c','usuarios.crear','Crear empleados','usuarios','crear','2026-05-24 09:17:53'),('4c67e7a4-5b69-45fd-9544-170568f63446','asignaciones.crear','Crear asignaciones','asignaciones','crear','2026-05-24 09:17:53'),('540dbaef-e3d9-46f8-ac2a-b76389982d47','compras.aprobar','Aprobar o rechazar solicitudes de compra','compras','aprobar','2026-06-01 23:36:06'),('665bb238-7af9-44d4-8a21-a8230de7ad9e','auditoria.exportar','Exportar log de auditoría','auditoria','exportar','2026-05-24 09:17:53'),('6a1aabd8-c4ef-43e5-a493-a4222eddb8cd','accesorios.editar','Editar accesorios existentes','accesorios','editar','2026-05-24 09:17:53'),('6fa2ee78-45f9-4c8e-ba70-eaa3a8e02f9f','accesorios.crear','Crear nuevos accesorios','accesorios','crear','2026-05-24 09:17:53'),('76b88081-a79a-44da-801e-07e59e700c31','empresas.eliminar','Eliminar empresas','empresas','eliminar','2026-05-24 09:17:53'),('783316e2-50d9-4472-92fe-a93155d38bb1','compras.gestionar_facturas','Gestionar facturas, proveedores y contratos','compras','gestionar_facturas','2026-06-01 23:36:06'),('7ca2d725-52e2-47c7-a860-a5785a26a9d8','estados.aprobar_baja','Aprobar o rechazar bajas de activos','estados','aprobar_baja','2026-06-12 07:20:57'),('8395e503-50ca-49d0-b5b9-de6156203170','activos.devolver','Registrar devoluciones de activos','activos','devolver','2026-05-24 09:17:53'),('88abb878-3692-40d6-8728-54774fa4ca63','asignaciones.ver','Ver asignaciones','asignaciones','ver','2026-05-24 09:17:53'),('895ecff0-dedd-413f-a585-988d64032ed7','usuarios.ver','Ver empleados','usuarios','ver','2026-05-24 09:17:53'),('94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6','actas.ver','Ver actas generadas','actas','ver','2026-05-24 09:17:53'),('95680ab8-6be2-42c8-9dbc-4e00acfa5219','servidores.eliminar','Desactivar / dar de baja servidores','servidores','eliminar','2026-05-25 11:58:22'),('a0f477ab-e9e1-4a8b-84d9-0fa2ead30278','accesorios.ver','Ver listado de accesorios','accesorios','ver','2026-05-24 09:17:53'),('a2a7130f-ed6f-479a-92c1-0d87ac32bf01','usuarios.editar','Editar empleados','usuarios','editar','2026-05-24 09:17:53'),('a4653525-d8f6-4c1b-a7ad-936a0801bc88','reservas.gestionar','Crear y cancelar reservas de activos/accesorios','reservas','gestionar','2026-06-18 12:07:58'),('b3e077c7-66a3-4fd5-932f-ec62265d6e1c','empresas.editar','Editar empresas','empresas','editar','2026-05-24 09:17:53'),('b680160c-11c9-48b0-b365-5624f8160c61','activos.editar','Editar activos existentes','activos','editar','2026-05-24 09:17:53'),('b774517c-e178-442d-ae7a-c4c2f32427ed','catalogos.editar','Crear y editar valores de catálogos','catalogos','editar','2026-06-04 20:39:04'),('b87016dd-4b5a-47f9-a61a-0d31ca89ff12','actas.generar','Generar nuevas actas PDF','actas','generar','2026-05-24 09:17:53'),('c97ea1a0-cf84-4f82-9b79-73a788a89188','compras.recepcionar','Registrar recepciones de mercancía','compras','recepcionar','2026-06-01 23:36:06'),('cad35f19-7865-43c0-bb51-201c1b9e59a5','compras.crear_solicitud','Crear solicitudes y órdenes de compra','compras','crear_solicitud','2026-06-01 23:36:06'),('ce061d3e-bb57-441a-a9ca-0e8343cc2e8f','estados.cambiar','Cambiar el estado de activos/accesorios','estados','cambiar','2026-06-12 07:20:57'),('d088ce93-3fb1-43c8-b4e6-72d2fae69a77','accesorios.devolver','Registrar devoluciones de accesorios','accesorios','devolver','2026-05-24 09:17:53'),('d2c8ec2a-da46-4875-bd67-cf7efb03838b','reportes.ver','Ver reportes','reportes','ver','2026-05-24 09:17:53'),('e4daf3c2-0eb4-4adf-a97c-8dad8960dd13','compras.ver','Ver módulo de compras','compras','ver','2026-06-01 23:36:06'),('e9ba9f7b-52c1-411c-aed1-62fb09b35cf8','compras.gestionar_garantias','Gestionar garantías','compras','gestionar_garantias','2026-06-01 23:36:06'),('ebcb240b-a1c1-4a0e-8e35-74bcb380e2de','servidores.editar','Editar información de servidores','servidores','editar','2026-05-25 11:58:22'),('ed02c948-a141-41a5-8a95-f00e90162022','activos.eliminar','Eliminar activos','activos','eliminar','2026-05-24 09:17:53');
/*!40000 ALTER TABLE `permisos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `proveedores`
--

DROP TABLE IF EXISTS `proveedores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `proveedores` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nit` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contacto_nombre` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ciudad` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_proveedor_empresa_nit` (`empresa_id`,`nit`),
  KEY `ix_proveedores_empresa_id` (`empresa_id`),
  CONSTRAINT `proveedores_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `proveedores`
--

LOCK TABLES `proveedores` WRITE;
/*!40000 ALTER TABLE `proveedores` DISABLE KEYS */;
INSERT INTO `proveedores` VALUES ('426a39e6-8e64-4e37-adde-b0930e8af6f9','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','P edit',NULL,'vendedor',NULL,NULL,NULL,NULL,1,'2026-06-02 07:35:45'),('95a7b748-d539-4987-8820-bd624c4066b2','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Proveedor Demo SAS','900-33e6bdb5','vendedor',NULL,NULL,NULL,NULL,1,'2026-06-02 08:10:52'),('9a8a3fc4-5a94-4836-adf8-8ffb3ce781e4','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Proveedor Demo SAS','900-0e92d50b','vendedor',NULL,NULL,NULL,NULL,1,'2026-06-01 23:39:52'),('ca84161f-9a3e-4cbe-a57d-969a95a4be2f','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Compunet','900.123.123-4','vendedor',NULL,NULL,'prueba@prueba.com','Medellin',1,'2026-06-22 12:38:49'),('f1035dea-cc68-46a9-aad7-3535f4e0ccda','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Proveedor Demo SAS','900-DEMO','vendedor',NULL,NULL,NULL,NULL,1,'2026-06-01 23:38:20');
/*!40000 ALTER TABLE `proveedores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recepcion_items`
--

DROP TABLE IF EXISTS `recepcion_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recepcion_items` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recepcion_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `solicitud_item_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descripcion` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cantidad_esperada` int NOT NULL,
  `cantidad_recibida` int NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observacion` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo_creado_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accesorio_creado_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `solicitud_item_id` (`solicitud_item_id`),
  KEY `activo_creado_id` (`activo_creado_id`),
  KEY `accesorio_creado_id` (`accesorio_creado_id`),
  KEY `ix_recepcion_items_recepcion_id` (`recepcion_id`),
  CONSTRAINT `recepcion_items_ibfk_1` FOREIGN KEY (`recepcion_id`) REFERENCES `recepciones` (`id`),
  CONSTRAINT `recepcion_items_ibfk_2` FOREIGN KEY (`solicitud_item_id`) REFERENCES `solicitud_items` (`id`),
  CONSTRAINT `recepcion_items_ibfk_3` FOREIGN KEY (`activo_creado_id`) REFERENCES `activos` (`id`),
  CONSTRAINT `recepcion_items_ibfk_4` FOREIGN KEY (`accesorio_creado_id`) REFERENCES `accesorios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recepcion_items`
--

LOCK TABLES `recepcion_items` WRITE;
/*!40000 ALTER TABLE `recepcion_items` DISABLE KEYS */;
INSERT INTO `recepcion_items` VALUES ('2795c6d9-7a2d-41dc-8346-10a7bfef19cb','085fb49a-5ef2-4351-bc58-c7a3bbea4c5a','12e0f4ce-25f3-4179-90d3-927e4eceeeb9','Combo teclado y mouse logitec',3,3,'ok',NULL,NULL,NULL,'b74360f1-43a0-4afa-bb9b-1df3b166f8a3'),('3ff5d1c3-22ef-426a-be7e-2192d0a6412c','9a5312d8-7208-4c04-92ce-d688a48efc97','8d613ff0-2b77-4c28-9b19-ca7b48fa94c9','Combo de teclado y mouse',1,1,'ok',NULL,NULL,NULL,'2be4ab50-60ec-4ba0-8c96-1096d1d0f83d'),('9b2d52e1-71f2-4d72-b75e-7190e2c040a5','9a5312d8-7208-4c04-92ce-d688a48efc97','42fc6453-6aa6-45c6-9a5e-80b7ed6d8417','Hp probook 445 G10',1,1,'ok','dfsdgbvda',NULL,'8d98751f-229c-4856-a2b6-71d1ab1dafef',NULL),('da529a43-e75d-44df-9257-2132705756db','ea024614-7a5f-4e44-bb85-625e03cc3e64','6745581c-fd62-4b38-afb0-7217d0c13dcf','Dell inspiron C456',1,1,'ok',NULL,NULL,'137b717e-f6fe-4953-8580-bcea57455301',NULL),('df163b0a-7a04-4f9c-8cff-86c3fe26f098','085fb49a-5ef2-4351-bc58-c7a3bbea4c5a','35146578-fdbc-49c0-bce6-c2d5df599d9c','Hp probook 445 G10',3,3,'ok',NULL,NULL,'1f6af8e6-1fc3-45d5-94d2-a9f66c7d8ab3',NULL);
/*!40000 ALTER TABLE `recepcion_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recepcion_items_creados`
--

DROP TABLE IF EXISTS `recepcion_items_creados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recepcion_items_creados` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recepcion_item_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_recurso` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recurso_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `placa` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_ric_recepcion_item` (`recepcion_item_id`),
  CONSTRAINT `recepcion_items_creados_ibfk_1` FOREIGN KEY (`recepcion_item_id`) REFERENCES `recepcion_items` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recepcion_items_creados`
--

LOCK TABLES `recepcion_items_creados` WRITE;
/*!40000 ALTER TABLE `recepcion_items_creados` DISABLE KEYS */;
INSERT INTO `recepcion_items_creados` VALUES ('3b31e09a-116d-4c63-ae03-a6a5645c5718','da529a43-e75d-44df-9257-2132705756db','activo','137b717e-f6fe-4953-8580-bcea57455301','SC0007','2026-06-22 17:02:41'),('4e6d6012-193d-4983-ba9b-41d5c381ce0c','3ff5d1c3-22ef-426a-be7e-2192d0a6412c','accesorio','2be4ab50-60ec-4ba0-8c96-1096d1d0f83d','SCA0002','2026-06-22 14:23:26'),('52458fe9-051f-4fc9-9afb-345028162454','2795c6d9-7a2d-41dc-8346-10a7bfef19cb','accesorio','bfad7466-a71f-4500-a7c4-a69c737f39e2','SCA0003','2026-06-22 16:40:53'),('5b51fe79-3165-4447-813b-0587a7bed636','2795c6d9-7a2d-41dc-8346-10a7bfef19cb','accesorio','86c964a2-7cc4-41f2-8cb6-f6f7e904e727','SCA0004','2026-06-22 16:41:27'),('a5a9245d-9345-4baa-be4d-02715ab2d6a8','df163b0a-7a04-4f9c-8cff-86c3fe26f098','activo','2c07ea7d-9850-40b4-b071-8eeb992090ed','SC0005','2026-06-22 16:44:04'),('d529a668-7ea2-4faa-bab5-67d01480099f','2795c6d9-7a2d-41dc-8346-10a7bfef19cb','accesorio','b74360f1-43a0-4afa-bb9b-1df3b166f8a3','SCA0005','2026-06-22 16:42:08'),('e36fc1fa-fc7f-4121-833a-84cf45556a10','9b2d52e1-71f2-4d72-b75e-7190e2c040a5','activo','8d98751f-229c-4856-a2b6-71d1ab1dafef','SC0003','2026-06-22 14:20:53'),('f3812b10-ee86-4ae4-b099-b5b10d3bf82e','df163b0a-7a04-4f9c-8cff-86c3fe26f098','activo','d7371cb3-6617-43b9-8fda-045bf96a9e14','SC0004','2026-06-22 16:43:23'),('f57cadec-cf60-4659-8bde-79b5387c1a41','df163b0a-7a04-4f9c-8cff-86c3fe26f098','activo','1f6af8e6-1fc3-45d5-94d2-a9f66c7d8ab3','SC0006','2026-06-22 16:44:31');
/*!40000 ALTER TABLE `recepcion_items_creados` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recepciones`
--

DROP TABLE IF EXISTS `recepciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recepciones` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `orden_compra_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recibido_por_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_recepcion` date NOT NULL,
  `estado` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `novedades` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `recibido_por_id` (`recibido_por_id`),
  KEY `ix_recepciones_orden_compra_id` (`orden_compra_id`),
  KEY `ix_recepciones_empresa_id` (`empresa_id`),
  CONSTRAINT `recepciones_ibfk_1` FOREIGN KEY (`orden_compra_id`) REFERENCES `ordenes_compra` (`id`),
  CONSTRAINT `recepciones_ibfk_2` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `recepciones_ibfk_3` FOREIGN KEY (`recibido_por_id`) REFERENCES `usuarios_sistema` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recepciones`
--

LOCK TABLES `recepciones` WRITE;
/*!40000 ALTER TABLE `recepciones` DISABLE KEYS */;
INSERT INTO `recepciones` VALUES ('085fb49a-5ef2-4351-bc58-c7a3bbea4c5a','713aa0b4-6d06-47da-ba35-0b5db5e10557','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22','recibida_completa',NULL,NULL,'2026-06-22 14:55:27'),('9a5312d8-7208-4c04-92ce-d688a48efc97','618afaf9-7bf0-45a5-afab-a5fdd700e4c1','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22','recibida_completa',NULL,NULL,'2026-06-22 12:45:19'),('ea024614-7a5f-4e44-bb85-625e03cc3e64','e163b247-73fb-4e0a-b56a-cedb7df293be','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22','recibida_completa',NULL,NULL,'2026-06-22 17:01:34');
/*!40000 ALTER TABLE `recepciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recordatorios_firma`
--

DROP TABLE IF EXISTS `recordatorios_firma`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recordatorios_firma` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acta_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enviado_a` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `numero_recordatorio` int NOT NULL DEFAULT '1',
  `fecha_envio` datetime DEFAULT CURRENT_TIMESTAMP,
  `escalado_admin` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `acta_id` (`acta_id`),
  KEY `token_id` (`token_id`),
  CONSTRAINT `recordatorios_firma_ibfk_1` FOREIGN KEY (`acta_id`) REFERENCES `actas_entrega` (`id`),
  CONSTRAINT `recordatorios_firma_ibfk_2` FOREIGN KEY (`token_id`) REFERENCES `firma_tokens` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recordatorios_firma`
--

LOCK TABLES `recordatorios_firma` WRITE;
/*!40000 ALTER TABLE `recordatorios_firma` DISABLE KEYS */;
/*!40000 ALTER TABLE `recordatorios_firma` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `reserva_items`
--

DROP TABLE IF EXISTS `reserva_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reserva_items` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reserva_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_recurso` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recurso_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `placa` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'reservado',
  PRIMARY KEY (`id`),
  KEY `reserva_id` (`reserva_id`),
  CONSTRAINT `reserva_items_ibfk_1` FOREIGN KEY (`reserva_id`) REFERENCES `reservas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reserva_items`
--

LOCK TABLES `reserva_items` WRITE;
/*!40000 ALTER TABLE `reserva_items` DISABLE KEYS */;
/*!40000 ALTER TABLE `reserva_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `reservas`
--

DROP TABLE IF EXISTS `reservas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reservas` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `numero_alta` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_unicode_ci,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_limite` date NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'activa',
  `creado_por_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `fecha_cierre` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  CONSTRAINT `reservas_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reservas`
--

LOCK TABLES `reservas` WRITE;
/*!40000 ALTER TABLE `reservas` DISABLE KEYS */;
/*!40000 ALTER TABLE `reservas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rol_permisos`
--

DROP TABLE IF EXISTS `rol_permisos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rol_permisos` (
  `rol_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `permiso_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`rol_id`,`permiso_id`),
  KEY `permiso_id` (`permiso_id`),
  CONSTRAINT `rol_permisos_ibfk_1` FOREIGN KEY (`rol_id`) REFERENCES `roles` (`id`),
  CONSTRAINT `rol_permisos_ibfk_2` FOREIGN KEY (`permiso_id`) REFERENCES `permisos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rol_permisos`
--

LOCK TABLES `rol_permisos` WRITE;
/*!40000 ALTER TABLE `rol_permisos` DISABLE KEYS */;
INSERT INTO `rol_permisos` VALUES ('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','0084505b-3d58-4116-aa1d-391841126291'),('28d29689-17be-49b4-a235-ed1df78ba967','0084505b-3d58-4116-aa1d-391841126291'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','0084505b-3d58-4116-aa1d-391841126291'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','051dd8c6-1ae3-4b99-94b1-8025834cc930'),('28d29689-17be-49b4-a235-ed1df78ba967','051dd8c6-1ae3-4b99-94b1-8025834cc930'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','051dd8c6-1ae3-4b99-94b1-8025834cc930'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','092130d7-4b99-4617-b219-d11bed979fce'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','092130d7-4b99-4617-b219-d11bed979fce'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','092130d7-4b99-4617-b219-d11bed979fce'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','092130d7-4b99-4617-b219-d11bed979fce'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','09fe697d-2dd8-40db-a236-5335651344e4'),('28d29689-17be-49b4-a235-ed1df78ba967','09fe697d-2dd8-40db-a236-5335651344e4'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','09fe697d-2dd8-40db-a236-5335651344e4'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','13110d43-63ec-4b35-a9c4-52104a7d2e01'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','13110d43-63ec-4b35-a9c4-52104a7d2e01'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','1a345a68-593c-46b9-abd5-4ef4bc73f4a1'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','1a345a68-593c-46b9-abd5-4ef4bc73f4a1'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','1a345a68-593c-46b9-abd5-4ef4bc73f4a1'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','212e9312-3860-43ae-8ee1-40d2a1bc1219'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','212e9312-3860-43ae-8ee1-40d2a1bc1219'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','217f218f-076a-4aee-b42a-e80527d11ad3'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','217f218f-076a-4aee-b42a-e80527d11ad3'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','253e3798-8557-4b8c-913e-c09675c870f7'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','299e8df4-ca25-4948-824f-92a08a744692'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','299e8df4-ca25-4948-824f-92a08a744692'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','299e8df4-ca25-4948-824f-92a08a744692'),('28d29689-17be-49b4-a235-ed1df78ba967','299e8df4-ca25-4948-824f-92a08a744692'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','299e8df4-ca25-4948-824f-92a08a744692'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','299e8df4-ca25-4948-824f-92a08a744692'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','32801561-71df-4e26-a890-4da91f85489b'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','32801561-71df-4e26-a890-4da91f85489b'),('28d29689-17be-49b4-a235-ed1df78ba967','32801561-71df-4e26-a890-4da91f85489b'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','32801561-71df-4e26-a890-4da91f85489b'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','34165deb-1f8f-4645-8c46-de403d62f5b6'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','34165deb-1f8f-4645-8c46-de403d62f5b6'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','34165deb-1f8f-4645-8c46-de403d62f5b6'),('28d29689-17be-49b4-a235-ed1df78ba967','34165deb-1f8f-4645-8c46-de403d62f5b6'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','34165deb-1f8f-4645-8c46-de403d62f5b6'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','34165deb-1f8f-4645-8c46-de403d62f5b6'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','349eaaf6-5379-4473-aafa-de53b50a9825'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','349eaaf6-5379-4473-aafa-de53b50a9825'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','349eaaf6-5379-4473-aafa-de53b50a9825'),('28d29689-17be-49b4-a235-ed1df78ba967','349eaaf6-5379-4473-aafa-de53b50a9825'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','349eaaf6-5379-4473-aafa-de53b50a9825'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','349eaaf6-5379-4473-aafa-de53b50a9825'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','36ec0020-535f-4dfb-9a6b-972130d195e9'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','36ec0020-535f-4dfb-9a6b-972130d195e9'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','41e864f5-a4a7-4328-8612-362c4a995662'),('28d29689-17be-49b4-a235-ed1df78ba967','41e864f5-a4a7-4328-8612-362c4a995662'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','41e864f5-a4a7-4328-8612-362c4a995662'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','43c8e1c5-a245-48ff-9460-78920a3dea9c'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','43c8e1c5-a245-48ff-9460-78920a3dea9c'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','458b0ac6-0196-4576-a3de-15ebb353809c'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','458b0ac6-0196-4576-a3de-15ebb353809c'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','458b0ac6-0196-4576-a3de-15ebb353809c'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','4c67e7a4-5b69-45fd-9544-170568f63446'),('28d29689-17be-49b4-a235-ed1df78ba967','4c67e7a4-5b69-45fd-9544-170568f63446'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','4c67e7a4-5b69-45fd-9544-170568f63446'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','540dbaef-e3d9-46f8-ac2a-b76389982d47'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','540dbaef-e3d9-46f8-ac2a-b76389982d47'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','665bb238-7af9-44d4-8a21-a8230de7ad9e'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','665bb238-7af9-44d4-8a21-a8230de7ad9e'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','665bb238-7af9-44d4-8a21-a8230de7ad9e'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','6a1aabd8-c4ef-43e5-a493-a4222eddb8cd'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','6a1aabd8-c4ef-43e5-a493-a4222eddb8cd'),('28d29689-17be-49b4-a235-ed1df78ba967','6a1aabd8-c4ef-43e5-a493-a4222eddb8cd'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','6a1aabd8-c4ef-43e5-a493-a4222eddb8cd'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','6fa2ee78-45f9-4c8e-ba70-eaa3a8e02f9f'),('28d29689-17be-49b4-a235-ed1df78ba967','6fa2ee78-45f9-4c8e-ba70-eaa3a8e02f9f'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','6fa2ee78-45f9-4c8e-ba70-eaa3a8e02f9f'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','76b88081-a79a-44da-801e-07e59e700c31'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','783316e2-50d9-4472-92fe-a93155d38bb1'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','783316e2-50d9-4472-92fe-a93155d38bb1'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','7ca2d725-52e2-47c7-a860-a5785a26a9d8'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','7ca2d725-52e2-47c7-a860-a5785a26a9d8'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','8395e503-50ca-49d0-b5b9-de6156203170'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','8395e503-50ca-49d0-b5b9-de6156203170'),('28d29689-17be-49b4-a235-ed1df78ba967','8395e503-50ca-49d0-b5b9-de6156203170'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','8395e503-50ca-49d0-b5b9-de6156203170'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','88abb878-3692-40d6-8728-54774fa4ca63'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','88abb878-3692-40d6-8728-54774fa4ca63'),('28d29689-17be-49b4-a235-ed1df78ba967','88abb878-3692-40d6-8728-54774fa4ca63'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','88abb878-3692-40d6-8728-54774fa4ca63'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','88abb878-3692-40d6-8728-54774fa4ca63'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','895ecff0-dedd-413f-a585-988d64032ed7'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','895ecff0-dedd-413f-a585-988d64032ed7'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','895ecff0-dedd-413f-a585-988d64032ed7'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','895ecff0-dedd-413f-a585-988d64032ed7'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6'),('28d29689-17be-49b4-a235-ed1df78ba967','94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','94c3fa4e-4eb1-49c0-98a8-7ecbca1600e6'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','95680ab8-6be2-42c8-9dbc-4e00acfa5219'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','95680ab8-6be2-42c8-9dbc-4e00acfa5219'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','a0f477ab-e9e1-4a8b-84d9-0fa2ead30278'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','a0f477ab-e9e1-4a8b-84d9-0fa2ead30278'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','a0f477ab-e9e1-4a8b-84d9-0fa2ead30278'),('28d29689-17be-49b4-a235-ed1df78ba967','a0f477ab-e9e1-4a8b-84d9-0fa2ead30278'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','a0f477ab-e9e1-4a8b-84d9-0fa2ead30278'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','a0f477ab-e9e1-4a8b-84d9-0fa2ead30278'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','a2a7130f-ed6f-479a-92c1-0d87ac32bf01'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','a2a7130f-ed6f-479a-92c1-0d87ac32bf01'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','a2a7130f-ed6f-479a-92c1-0d87ac32bf01'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','a4653525-d8f6-4c1b-a7ad-936a0801bc88'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','a4653525-d8f6-4c1b-a7ad-936a0801bc88'),('28d29689-17be-49b4-a235-ed1df78ba967','a4653525-d8f6-4c1b-a7ad-936a0801bc88'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','a4653525-d8f6-4c1b-a7ad-936a0801bc88'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','b3e077c7-66a3-4fd5-932f-ec62265d6e1c'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','b3e077c7-66a3-4fd5-932f-ec62265d6e1c'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','b680160c-11c9-48b0-b365-5624f8160c61'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','b680160c-11c9-48b0-b365-5624f8160c61'),('28d29689-17be-49b4-a235-ed1df78ba967','b680160c-11c9-48b0-b365-5624f8160c61'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','b680160c-11c9-48b0-b365-5624f8160c61'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','b774517c-e178-442d-ae7a-c4c2f32427ed'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','b774517c-e178-442d-ae7a-c4c2f32427ed'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','b87016dd-4b5a-47f9-a61a-0d31ca89ff12'),('28d29689-17be-49b4-a235-ed1df78ba967','b87016dd-4b5a-47f9-a61a-0d31ca89ff12'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','b87016dd-4b5a-47f9-a61a-0d31ca89ff12'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','b87016dd-4b5a-47f9-a61a-0d31ca89ff12'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','c97ea1a0-cf84-4f82-9b79-73a788a89188'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','c97ea1a0-cf84-4f82-9b79-73a788a89188'),('28d29689-17be-49b4-a235-ed1df78ba967','c97ea1a0-cf84-4f82-9b79-73a788a89188'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','c97ea1a0-cf84-4f82-9b79-73a788a89188'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','cad35f19-7865-43c0-bb51-201c1b9e59a5'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','cad35f19-7865-43c0-bb51-201c1b9e59a5'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','ce061d3e-bb57-441a-a9ca-0e8343cc2e8f'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','ce061d3e-bb57-441a-a9ca-0e8343cc2e8f'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','ce061d3e-bb57-441a-a9ca-0e8343cc2e8f'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','d088ce93-3fb1-43c8-b4e6-72d2fae69a77'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','d088ce93-3fb1-43c8-b4e6-72d2fae69a77'),('28d29689-17be-49b4-a235-ed1df78ba967','d088ce93-3fb1-43c8-b4e6-72d2fae69a77'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','d088ce93-3fb1-43c8-b4e6-72d2fae69a77'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','d2c8ec2a-da46-4875-bd67-cf7efb03838b'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','d2c8ec2a-da46-4875-bd67-cf7efb03838b'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','d2c8ec2a-da46-4875-bd67-cf7efb03838b'),('28d29689-17be-49b4-a235-ed1df78ba967','d2c8ec2a-da46-4875-bd67-cf7efb03838b'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','d2c8ec2a-da46-4875-bd67-cf7efb03838b'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','d2c8ec2a-da46-4875-bd67-cf7efb03838b'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','e4daf3c2-0eb4-4adf-a97c-8dad8960dd13'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','e4daf3c2-0eb4-4adf-a97c-8dad8960dd13'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','e4daf3c2-0eb4-4adf-a97c-8dad8960dd13'),('28d29689-17be-49b4-a235-ed1df78ba967','e4daf3c2-0eb4-4adf-a97c-8dad8960dd13'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','e4daf3c2-0eb4-4adf-a97c-8dad8960dd13'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','e4daf3c2-0eb4-4adf-a97c-8dad8960dd13'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','e9ba9f7b-52c1-411c-aed1-62fb09b35cf8'),('28d29689-17be-49b4-a235-ed1df78ba967','e9ba9f7b-52c1-411c-aed1-62fb09b35cf8'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','e9ba9f7b-52c1-411c-aed1-62fb09b35cf8'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','ebcb240b-a1c1-4a0e-8e35-74bcb380e2de'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','ebcb240b-a1c1-4a0e-8e35-74bcb380e2de'),('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','ed02c948-a141-41a5-8a95-f00e90162022'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','ed02c948-a141-41a5-8a95-f00e90162022');
/*!40000 ALTER TABLE `rol_permisos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES ('0b709fc1-a8ed-4c3f-8d42-36ba9450ac14','admin','Administración completa por empresa',1,'2026-05-24 09:17:53'),('0eec6d8d-78bc-4e0a-95c0-3d4466aef798','auditoria','Solo lectura y exportación de reportes',1,'2026-05-24 09:17:53'),('1a57b660-9500-4547-bd0e-7043f3c16fbc','soporte_ti','Operación básica: edición y devoluciones',1,'2026-05-24 09:17:53'),('28d29689-17be-49b4-a235-ed1df78ba967','analista_activos','Gestión completa de activos y asignaciones',1,'2026-05-24 09:17:53'),('48ead67d-fd1b-47c9-8d7b-65383c4686b2','rrhh','Gestión de empleados y consulta de asignaciones',1,'2026-05-24 09:17:53'),('a08196f3-5a93-48c7-a6e8-f2b1d0c5193f','super_admin','Acceso total al sistema, todas las empresas',1,'2026-05-24 09:17:53');
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `servicios_servidor`
--

DROP TABLE IF EXISTS `servicios_servidor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servicios_servidor` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `servidor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre_servicio` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `puerto` int DEFAULT NULL,
  `protocolo` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `servidor_id` (`servidor_id`),
  CONSTRAINT `servicios_servidor_ibfk_1` FOREIGN KEY (`servidor_id`) REFERENCES `servidores` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `servicios_servidor`
--

LOCK TABLES `servicios_servidor` WRITE;
/*!40000 ALTER TABLE `servicios_servidor` DISABLE KEYS */;
/*!40000 ALTER TABLE `servicios_servidor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `servidor_herramientas`
--

DROP TABLE IF EXISTS `servidor_herramientas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servidor_herramientas` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `servidor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `herramienta_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `version` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_instalacion` date DEFAULT NULL,
  `ultima_actualizacion` date DEFAULT NULL,
  `notas` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_servidor_herramienta` (`servidor_id`,`herramienta_id`),
  KEY `herramienta_id` (`herramienta_id`),
  CONSTRAINT `servidor_herramientas_ibfk_1` FOREIGN KEY (`servidor_id`) REFERENCES `servidores` (`id`),
  CONSTRAINT `servidor_herramientas_ibfk_2` FOREIGN KEY (`herramienta_id`) REFERENCES `herramientas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `servidor_herramientas`
--

LOCK TABLES `servidor_herramientas` WRITE;
/*!40000 ALTER TABLE `servidor_herramientas` DISABLE KEYS */;
INSERT INTO `servidor_herramientas` VALUES ('44d5d5ed-8fd5-4a70-b342-0fcd999c7f45','ff0a6654-dfed-4443-818d-412d00aa5bf6','b41aaae0-7598-4154-9e25-3b0b5dab2c69','instalado','7.4',NULL,NULL,NULL,'2026-05-29 08:24:27'),('ce02339a-8e89-46bf-a2bd-132650d7476d','05417c82-46b3-47d3-93e4-ff762490e028','19e0b855-7515-48b4-a3d4-0e33fd8fb499','configurado',NULL,NULL,NULL,NULL,'2026-05-29 08:53:35'),('dab95556-17fd-4440-9531-6c3a0fafca7e','05417c82-46b3-47d3-93e4-ff762490e028','50a77bbd-0676-4028-a762-e45bde0d7847','instalado','7.2.12',NULL,NULL,NULL,'2026-05-29 08:52:30');
/*!40000 ALTER TABLE `servidor_herramientas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `servidores`
--

DROP TABLE IF EXISTS `servidores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servidores` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `hostname` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_servicio` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `kawak_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `glpi_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_servidor_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ambiente_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `criticidad_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ubicacion_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `so_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `procesador` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `memoria_ram` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disco` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ip_lan` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ip_salida` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `pendientes` text COLLATE utf8mb4_unicode_ci,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_servidor_empresa_hostname` (`empresa_id`,`hostname`),
  KEY `tipo_servidor_id` (`tipo_servidor_id`),
  KEY `ambiente_id` (`ambiente_id`),
  KEY `criticidad_id` (`criticidad_id`),
  KEY `estado_id` (`estado_id`),
  KEY `ubicacion_id` (`ubicacion_id`),
  KEY `so_id` (`so_id`),
  CONSTRAINT `servidores_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `servidores_ibfk_2` FOREIGN KEY (`tipo_servidor_id`) REFERENCES `tipos_servidor` (`id`),
  CONSTRAINT `servidores_ibfk_3` FOREIGN KEY (`ambiente_id`) REFERENCES `ambientes` (`id`),
  CONSTRAINT `servidores_ibfk_4` FOREIGN KEY (`criticidad_id`) REFERENCES `criticidades` (`id`),
  CONSTRAINT `servidores_ibfk_5` FOREIGN KEY (`estado_id`) REFERENCES `estados_servidor` (`id`),
  CONSTRAINT `servidores_ibfk_6` FOREIGN KEY (`ubicacion_id`) REFERENCES `ubicaciones` (`id`),
  CONSTRAINT `servidores_ibfk_7` FOREIGN KEY (`so_id`) REFERENCES `sistemas_operativos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `servidores`
--

LOCK TABLES `servidores` WRITE;
/*!40000 ALTER TABLE `servidores` DISABLE KEYS */;
INSERT INTO `servidores` VALUES ('05417c82-46b3-47d3-93e4-ff762490e028','3a7a8133-25a7-44ab-a345-70fa0b6d8f6b','SRV-TEST-VERIF-01','srv-test-verif-01.local',NULL,NULL,NULL,'f44c058c-ee01-451c-9b49-7a935a193eed','719c715b-ce03-4077-90df-4ea2bb8da6ed','e9544258-8b99-42d1-8b38-9f1e361fcc47','71095bfe-d7c4-4cb1-97f3-afca6029d6c2',NULL,'112b852e-a769-47a0-b440-3155c83cafe1','Intel Xeon E5-2680','64 GB DDR4','500GB','10.0.0.251',NULL,'Test observacion verificacion',NULL,0,'2026-05-25 12:48:15','2026-05-26 07:40:43'),('ff0a6654-dfed-4443-818d-412d00aa5bf6','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Hefesto','Hefesto','ADV0034',NULL,NULL,'f44c058c-ee01-451c-9b49-7a935a193eed','719c715b-ce03-4077-90df-4ea2bb8da6ed','4301ff83-7383-4e48-9f9a-913c8caa6556','71095bfe-d7c4-4cb1-97f3-afca6029d6c2',NULL,'e177df34-22c1-46b2-abe3-691a523437e2','4 Core','6GB','50GB','10.4.1.3',NULL,NULL,NULL,1,'2026-05-25 14:03:32','2026-05-27 11:08:02');
/*!40000 ALTER TABLE `servidores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sistemas_operativos`
--

DROP TABLE IF EXISTS `sistemas_operativos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sistemas_operativos` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `familia` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `soporte_activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sistemas_operativos`
--

LOCK TABLES `sistemas_operativos` WRITE;
/*!40000 ALTER TABLE `sistemas_operativos` DISABLE KEYS */;
INSERT INTO `sistemas_operativos` VALUES ('077e9eed-c3da-4bc4-934e-c897e9450dd5','Ubuntu Server 20.04 LTS','Linux',1),('112b852e-a769-47a0-b440-3155c83cafe1','CentOS Stream 9','Linux',1),('146e747f-6cea-4db7-9c47-909caafb7d5a','VMware ESXi 7.0','Hypervisor',1),('27144b8b-161e-4b2a-84d2-22961af45024','Windows Server 2022','Windows',1),('4f7c02d4-55e8-4c73-99a7-63b9ae22c913','Ubuntu Server 22.04 LTS','Linux',1),('51d6fcb9-4fac-4554-b758-f976330ea361','Debian 12 (Bookworm)','Linux',1),('5700f1d7-130c-4a5c-8f5b-37b9de459a11','Windows Server 2019','Windows',1),('60afd12c-7f81-49ab-be15-81580b793898','Red Hat Enterprise Linux 7','Linux',0),('75beddd6-7d6c-4f6b-b9ad-74968f48c615','FreeBSD 14','BSD',1),('833236cb-f7d0-4647-bdb0-f98889740320','Red Hat Enterprise Linux 8','Linux',1),('8a9456f2-d19b-4006-8f3c-16b9d5082d0d','Rocky Linux 9','Linux',1),('90264ee0-d381-44d4-9007-27cda6ea1cb3','Ubuntu Server 24.04 LTS','Linux',1),('a5f8d08e-e087-4fca-839c-bffab75001d0','Windows Server 2016','Windows',1),('c198f8f5-149c-4b97-8509-46dc0f69140c','Proxmox VE 8','Hypervisor',1),('d6ec7c3a-d674-445e-ad59-7c5cbfd19d64','VMware ESXi 8.0','Hypervisor',1),('da30dcaa-3940-40c6-9e5c-a3f0a162b9b8','AlmaLinux 9','Linux',1),('e177df34-22c1-46b2-abe3-691a523437e2','Windows Server 2012 R2','Windows',0),('e67edc03-a7fa-4989-989c-4b6e975af66f','SUSE Linux Enterprise Server 15','Linux',1),('eb2597a6-4658-4d76-b902-35b4887468a1','Red Hat Enterprise Linux 9','Linux',1);
/*!40000 ALTER TABLE `sistemas_operativos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `solicitud_items`
--

DROP TABLE IF EXISTS `solicitud_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `solicitud_items` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `solicitud_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_item` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_adquisicion` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cantidad` int NOT NULL,
  `valor_unitario_estimado` decimal(14,2) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_solicitud_items_solicitud_id` (`solicitud_id`),
  CONSTRAINT `solicitud_items_ibfk_1` FOREIGN KEY (`solicitud_id`) REFERENCES `solicitudes_compra` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `solicitud_items`
--

LOCK TABLES `solicitud_items` WRITE;
/*!40000 ALTER TABLE `solicitud_items` DISABLE KEYS */;
INSERT INTO `solicitud_items` VALUES ('12e0f4ce-25f3-4179-90d3-927e4eceeeb9','acae5078-31fe-4593-91de-60faa3c17d0b','Combo teclado y mouse logitec','activo','compra',3,150000.00,'2026-06-22 14:51:59'),('35146578-fdbc-49c0-bce6-c2d5df599d9c','acae5078-31fe-4593-91de-60faa3c17d0b','Hp probook 445 G10','activo','compra',3,4500000.00,'2026-06-22 14:51:59'),('42fc6453-6aa6-45c6-9a5e-80b7ed6d8417','881d9db2-cc0b-4e82-8b9e-516d8a8dec79','Hp probook 445 G10','activo','compra',1,4500000.00,'2026-06-22 12:33:56'),('6745581c-fd62-4b38-afb0-7217d0c13dcf','a4ca60fd-17b7-42ea-b9f7-7591f70a0946','Dell inspiron C456','activo','alquiler',1,NULL,'2026-06-22 17:00:02'),('8d613ff0-2b77-4c28-9b19-ca7b48fa94c9','881d9db2-cc0b-4e82-8b9e-516d8a8dec79','Combo de teclado y mouse','accesorio','compra',1,150000.00,'2026-06-22 12:33:56');
/*!40000 ALTER TABLE `solicitud_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `solicitudes_compra`
--

DROP TABLE IF EXISTS `solicitudes_compra`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `solicitudes_compra` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `solicitante_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `justificacion` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aprobado_por_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_aprobacion` datetime DEFAULT NULL,
  `motivo_rechazo` text COLLATE utf8mb4_unicode_ci,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `numero_solicitud` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `titulo` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `motivo_cancelacion` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `solicitante_id` (`solicitante_id`),
  KEY `aprobado_por_id` (`aprobado_por_id`),
  KEY `ix_solicitudes_compra_empresa_id` (`empresa_id`),
  KEY `ix_solicitudes_compra_estado` (`estado`),
  CONSTRAINT `solicitudes_compra_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`),
  CONSTRAINT `solicitudes_compra_ibfk_2` FOREIGN KEY (`solicitante_id`) REFERENCES `usuarios_sistema` (`id`),
  CONSTRAINT `solicitudes_compra_ibfk_3` FOREIGN KEY (`aprobado_por_id`) REFERENCES `usuarios_sistema` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `solicitudes_compra`
--

LOCK TABLES `solicitudes_compra` WRITE;
/*!40000 ALTER TABLE `solicitudes_compra` DISABLE KEYS */;
INSERT INTO `solicitudes_compra` VALUES ('881d9db2-cc0b-4e82-8b9e-516d8a8dec79','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1e402ada-9649-4a6b-8f32-e82aae8be5e3','Cargo nuevo requiere equipo portatil','recibida','1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22 12:34:55',NULL,'Urgente','2026-06-22 12:33:03','2026-06-22 12:47:08','SC-2026-001','Equipo para el area de TI',NULL),('a4ca60fd-17b7-42ea-b9f7-7591f70a0946','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1e402ada-9649-4a6b-8f32-e82aae8be5e3','aumento de personal','recibida','1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22 17:00:21',NULL,NULL,'2026-06-22 17:00:02','2026-06-22 17:02:41','SC-2026-003','Alquiler equipos livecenter',NULL),('acae5078-31fe-4593-91de-60faa3c17d0b','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1e402ada-9649-4a6b-8f32-e82aae8be5e3','Renovación tecnología para el área de contraloría','recibida','1e402ada-9649-4a6b-8f32-e82aae8be5e3','2026-06-22 14:52:34',NULL,NULL,'2026-06-22 14:51:59','2026-06-22 16:44:31','SC-2026-002','Renovación tecnologia contraloria',NULL);
/*!40000 ALTER TABLE `solicitudes_compra` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tipos_servidor`
--

DROP TABLE IF EXISTS `tipos_servidor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tipos_servidor` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tipos_servidor`
--

LOCK TABLES `tipos_servidor` WRITE;
/*!40000 ALTER TABLE `tipos_servidor` DISABLE KEYS */;
INSERT INTO `tipos_servidor` VALUES ('3ee4fc65-ea7b-4ae2-8e96-202f277361ae','Bastión','Servidor de salto / bastión SSH'),('9685d378-9b82-4a40-82c0-1bc59a0edae7','Físico','Servidor físico on-premise'),('9a6d7699-1eff-4906-acae-dd764b6f938b','Appliance','Dispositivo appliance dedicado'),('b182fab4-4ba3-45f7-96bc-bae6c62d0eb5','Contenedor','Contenedor Docker / LXC'),('f44c058c-ee01-451c-9b49-7a935a193eed','Virtual','Máquina virtual (VMware, Hyper-V, KVM)'),('fbbab929-cd9a-43d0-a8fa-770b712e4312','Cloud','Instancia de nube pública (AWS, Azure, GCP)');
/*!40000 ALTER TABLE `tipos_servidor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ubicaciones`
--

DROP TABLE IF EXISTS `ubicaciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ubicaciones` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ciudad` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pais` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descripcion` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ubicacion_empresa_nombre` (`empresa_id`,`nombre`),
  CONSTRAINT `ubicaciones_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ubicaciones`
--

LOCK TABLES `ubicaciones` WRITE;
/*!40000 ALTER TABLE `ubicaciones` DISABLE KEYS */;
/*!40000 ALTER TABLE `ubicaciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuario_roles`
--

DROP TABLE IF EXISTS `usuario_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario_roles` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `usuario_sistema_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rol_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `rol_id` (`rol_id`),
  KEY `empresa_id` (`empresa_id`),
  KEY `ix_usuario_roles_usr_emp` (`usuario_sistema_id`,`empresa_id`),
  CONSTRAINT `usuario_roles_ibfk_1` FOREIGN KEY (`usuario_sistema_id`) REFERENCES `usuarios_sistema` (`id`),
  CONSTRAINT `usuario_roles_ibfk_2` FOREIGN KEY (`rol_id`) REFERENCES `roles` (`id`),
  CONSTRAINT `usuario_roles_ibfk_3` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuario_roles`
--

LOCK TABLES `usuario_roles` WRITE;
/*!40000 ALTER TABLE `usuario_roles` DISABLE KEYS */;
INSERT INTO `usuario_roles` VALUES ('0d121f6d-bb32-43c8-a0bc-1a27f6d81fab','36ccb76d-6886-497a-ab23-b9159e7c7543','1a57b660-9500-4547-bd0e-7043f3c16fbc','3a7a8133-25a7-44ab-a345-70fa0b6d8f6b',1,'2026-06-24 09:09:18'),('414fb848-e4bb-4d90-b184-ccd75c8f90cf','36ccb76d-6886-497a-ab23-b9159e7c7543','1a57b660-9500-4547-bd0e-7043f3c16fbc','4676ae6d-5793-4630-8610-787c68005b49',1,'2026-06-24 09:09:24'),('54ed469f-abd4-490b-b65d-114b64fd3b9c','2ca0eb8f-789b-4891-b4fb-b70c0ef84d12','a08196f3-5a93-48c7-a6e8-f2b1d0c5193f',NULL,1,'2026-05-24 09:19:18'),('a42e75a3-3c83-4824-a040-efc9a0b77f2d','a45c7482-13b3-4616-8f44-62681c2f4f77','28d29689-17be-49b4-a235-ed1df78ba967','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',1,'2026-06-24 09:19:14'),('acf7b95d-5a33-474c-8266-330c51d06514','1e402ada-9649-4a6b-8f32-e82aae8be5e3','a08196f3-5a93-48c7-a6e8-f2b1d0c5193f',NULL,1,'2026-06-02 16:56:44'),('ee724b58-5c36-4838-863a-dd60db83c741','36ccb76d-6886-497a-ab23-b9159e7c7543','1a57b660-9500-4547-bd0e-7043f3c16fbc','09a4a3d5-2286-45da-99e9-54c0f5de5a7a',1,'2026-06-24 09:09:16'),('efc5be46-7de9-418d-b63e-98c978dbc6fb','a45c7482-13b3-4616-8f44-62681c2f4f77','28d29689-17be-49b4-a235-ed1df78ba967','3a7a8133-25a7-44ab-a345-70fa0b6d8f6b',1,'2026-06-24 09:19:22'),('f86552b4-c092-441e-9475-4180752c1add','36ccb76d-6886-497a-ab23-b9159e7c7543','1a57b660-9500-4547-bd0e-7043f3c16fbc','d68bd912-5d65-4548-a2a5-dbd197891028',1,'2026-06-24 09:09:21');
/*!40000 ALTER TABLE `usuario_roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `documento` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre_completo` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cargo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sede` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `unidad_negocio` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `empresa_id` (`empresa_id`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES ('0e894bc0-998d-4cb5-b2c3-19c344a2b3cc','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','12345678','Marlon Carrasquilla','Analista Senior','Tecnología','Medellin','ricardo.tamayo@outlook.com',NULL,'activo','2026-05-26 11:31:31','2026-06-20 14:50:05',NULL),('0f888ec9-5bbc-40e5-b460-dc44a34ed058','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','ZZTESTEMP1','ZZTEST Empleado',NULL,NULL,NULL,'zztest.emp@test.com',NULL,'activo','2026-06-18 12:24:08','2026-06-18 12:24:08',NULL),('234206dd-42f3-40b1-a66e-41d51f9f8781','3a7a8133-25a7-44ab-a345-70fa0b6d8f6b','1088306267','Rogelio Toro','Analista','Tecnología','Palacé','ricardo.tamayo@outlook.com',NULL,'activo','2026-05-24 15:30:16','2026-06-01 21:58:13',NULL),('6a0d72ca-407c-4345-aee9-8d7994e2b443','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','ZZTESTEMP1','ZZTEST Empleado',NULL,NULL,NULL,'zztest.emp@test.com',NULL,'activo','2026-06-18 12:24:58','2026-06-18 12:24:58',NULL),('7f0f43fd-8b63-4d93-840b-2aef84f35fa3','4676ae6d-5793-4630-8610-787c68005b49','10883226477','Pepito Perez','Coordinador','Taller','Medellin','ricardo.tamayo@outlook.com',NULL,'activo','2026-05-20 10:32:12','2026-05-30 11:46:44',NULL),('8ee93e22-ca2c-431d-9bfa-d6db9d4b585d','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','ZZTESTEMP1','ZZTEST Empleado',NULL,NULL,NULL,'zztest.emp@test.com',NULL,'activo','2026-06-18 12:24:35','2026-06-18 12:24:35',NULL),('f5c7e022-84d1-4632-b4ba-9c829536fd63','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','1045892310','Laura Gómez','Analista Senior','Tecnología','Medellín','ricardo.tamayo@outlook.com','3001234567','activo','2026-05-19 20:36:35','2026-05-30 11:58:15','Livecenter');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios_sistema`
--

DROP TABLE IF EXISTS `usuarios_sistema`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios_sistema` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `nombre` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rol` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `activo` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `empresa_id` (`empresa_id`),
  CONSTRAINT `usuarios_sistema_ibfk_1` FOREIGN KEY (`empresa_id`) REFERENCES `empresas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios_sistema`
--

LOCK TABLES `usuarios_sistema` WRITE;
/*!40000 ALTER TABLE `usuarios_sistema` DISABLE KEYS */;
INSERT INTO `usuarios_sistema` VALUES ('1e402ada-9649-4a6b-8f32-e82aae8be5e3','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Ricardo Tamayo','ricardo.tamayo@sociabpo.com','$2b$12$0VyDLHUcxhEzmr1jNSbHNOgOGd1uiMuFwEQeqWipwMeqe86AJI8vq','visualizador',1,'2026-06-02 16:56:25','2026-06-02 16:56:25'),('2ca0eb8f-789b-4891-b4fb-b70c0ef84d12',NULL,'Superadmin Ricardo Tamayo','admin@inventario.com','$2b$12$feQ91KsI/CQDc6t0gr06v.63k1ORY20SoxEHSwdXcEmF8T5CDpQT2','superadmin',1,'2026-05-19 20:22:40','2026-05-29 17:17:46'),('36ccb76d-6886-497a-ab23-b9159e7c7543','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Jhonny Montoya','jhonny.montoya@sociabpo.com','$2b$12$apjS/F1BAA/eW2Ymg0MhWeFzjueR3Lk2/saio4P.6OK5m7LfYzrkW','visualizador',1,'2026-06-24 09:08:59','2026-06-24 09:08:59'),('a45c7482-13b3-4616-8f44-62681c2f4f77','09a4a3d5-2286-45da-99e9-54c0f5de5a7a','Daniel Perez','Daniel.Perez@sociabpo.com','$2b$12$u.yk1BAcPo.Z7/RpUmwH0.mJODFeyMHXrWpXLc/dNgl4oLPCD6Dga','visualizador',1,'2026-06-24 09:19:00','2026-06-24 09:19:00');
/*!40000 ALTER TABLE `usuarios_sistema` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-24 10:28:28
