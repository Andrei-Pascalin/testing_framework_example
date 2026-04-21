"""
Database handler for test results received by FastApi server.
Manages SQLAlchemy ORM operations and database lifecycle.
"""
from __future__ import annotations


from typing import List, Optional, Dict, Any
from datetime import datetime

# from pathlib import Path
# import os

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from utils.my_logger import get_logger

log = get_logger(log_filename="database_handler.log")

Base = declarative_base()


class TestResultModel(Base):
    """SQLAlchemy ORM model for test results."""

    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_name = Column(String(255), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    text = Column(String(4096), nullable=True)
    start_time = Column(String(255), nullable=False)
    runtime = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now(), index=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "test_name": self.test_name,
            "success": self.success,
            "text": self.text,
            "start_time": self.start_time,
            "runtime": self.runtime,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DatabaseHandler:
    """
    database handler for managing test results.

    Handles:
    - Database initialization and table creation
    - Connection pooling and session management
    - CRUD operations (create, read, update, delete) for test results
    - Query capabilities with filtering
    - Error handling and logging
    """

    def __init__(
        self,
        database_url: str = "sqlite:///./test_results.db",
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """
        Initialize the database handler.

        Args:
            database_url: SQLAlchemy database URL. Defaults to SQLite local database.
            echo: If True, log all SQL statements. Defaults to False.
            pool_size: Number of connections to keep in the connection pool.
            max_overflow: Maximum overflow connections beyond pool_size.
        """
        self.database_url = database_url
        self.echo = echo

        try:
            # Create engine with connection pooling
            engine_kwargs = {
                "echo": echo,
            }

            # SQLite-specific configuration
            if "sqlite" in database_url:
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            else:
                # For other databases (PostgreSQL, MySQL, etc.)
                engine_kwargs["pool_size"] = pool_size
                engine_kwargs["max_overflow"] = max_overflow

            self.engine = create_engine(database_url, **engine_kwargs)
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            log.info(f"Database handler initialized with URL: {database_url}")
        except Exception as e:
            log.error(f"Failed to initialize database handler: {e}")
            raise

    def init_db(self) -> bool:
        """
        Initialize database and create tables if they don't exist.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            Base.metadata.create_all(bind=self.engine)
            log.info("Database tables created/verified successfully")
            return True
        except SQLAlchemyError as e:
            log.error(f"Database initialization error: {e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error during database initialization: {e}")
            return False

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            Session: SQLAlchemy session object.
        """
        return self.SessionLocal()

    def store_result(self, test_result: Dict[str, Any]) -> Optional[int]:
        """
        Store a test result in the database.

        Args:
            test_result: Dictionary containing test result data with keys:
                - test_name (str)
                - success (bool)
                - text (str)
                - start_time (str)
                - runtime (float)

        Returns:
            int: ID of stored result if successful, None otherwise.
        """
        session = None
        try:
            session = self.get_session()

            db_result = TestResultModel(
                test_name=test_result["test_name"],
                success=test_result["success"],
                text=test_result.get("text", ""),
                start_time=test_result["start_time"],
                runtime=test_result["runtime"],
            )

            session.add(db_result)
            session.commit()

            result_id = db_result.id
            log.debug(f"Test result stored successfully with ID: {result_id}")
            return result_id

        except KeyError as e:
            log.error(f"Missing required field in test result: {e}")
            if session:
                session.rollback()
            return None
        except SQLAlchemyError as e:
            log.error(f"Database error while storing result: {e}")
            if session:
                session.rollback()
            return None
        except Exception as e:
            log.error(f"Unexpected error while storing result: {e}")
            if session:
                session.rollback()
            return None
        finally:
            if session:
                session.close()

    def get_result_by_id(self, result_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a test result by ID.

        Args:
            result_id: ID of the test result.

        Returns:
            Dictionary with test result data if found, None otherwise.
        """
        session = None
        try:
            session = self.get_session()
            result = session.query(TestResultModel).filter(
                TestResultModel.id == result_id
            ).first()

            return result.to_dict() if result else None

        except SQLAlchemyError as e:
            log.error(f"Database error while retrieving result: {e}")
            return None
        finally:
            if session:
                session.close()

    def get_results_by_test_name(self, test_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all results for a specific test name.

        Args:
            test_name: Name of the test to search for.

        Returns:
            List of test result dictionaries.
        """
        session = None
        try:
            session = self.get_session()
            results = session.query(TestResultModel).filter(
                TestResultModel.test_name == test_name
            ).all()

            return [result.to_dict() for result in results]

        except SQLAlchemyError as e:
            log.error(f"Database error while retrieving results by test name: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_all_results(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve all test results with pagination.

        Args:
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            List of test result dictionaries.
        """
        session = None
        try:
            session = self.get_session()
            results = session.query(TestResultModel).order_by(
                TestResultModel.created_at.desc()
            ).offset(offset).limit(limit).all()

            return [result.to_dict() for result in results]

        except SQLAlchemyError as e:
            log.error(f"Database error while retrieving all results: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_results_by_status(
        self,
        success: bool,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve test results filtered by success status.

        Args:
            success: True for successful tests, False for failed tests.
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            List of test result dictionaries.
        """
        session = None
        try:
            session = self.get_session()
            results = session.query(TestResultModel).filter(
                TestResultModel.success == success
            ).order_by(
                TestResultModel.created_at.desc()
            ).offset(offset).limit(limit).all()

            return [result.to_dict() for result in results]

        except SQLAlchemyError as e:
            log.error(f"Database error while retrieving results by status: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_test_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about test results.

        Returns:
            Dictionary containing:
            - total_tests: Total number of tests
            - passed_tests: Number of passed tests
            - failed_tests: Number of failed tests
            - success_rate: Success rate percentage
            - avg_runtime: Average runtime in seconds
        """
        session = None
        try:
            session = self.get_session()

            total = session.query(TestResultModel).count()
            if total == 0:
                return {
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "success_rate": 0.0,
                    "avg_runtime": 0.0,
                }

            passed = session.query(TestResultModel).filter(
                TestResultModel.success == True
            ).count()
            failed = total - passed

            avg_runtime = session.query(TestResultModel.runtime).all()
            avg_runtime = sum([r[0] for r in avg_runtime]) / len(avg_runtime) if avg_runtime else 0

            return {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": round((passed / total) * 100, 2),
                "avg_runtime": round(avg_runtime, 2),
            }

        except SQLAlchemyError as e:
            log.error(f"Database error while retrieving statistics: {e}")
            return {}
        finally:
            if session:
                session.close()

    def delete_result_by_id(self, result_id: int) -> bool:
        """
        Delete a test result by ID.

        Args:
            result_id: ID of the test result to delete.

        Returns:
            bool: True if successful, False otherwise.
        """
        session = None
        try:
            session = self.get_session()
            result = session.query(TestResultModel).filter(
                TestResultModel.id == result_id
            ).first()

            if result:
                session.delete(result)
                session.commit()
                log.debug(f"Test result deleted: ID {result_id}")
                return True
            else:
                log.warning(f"Result not found for deletion: ID {result_id}")
                return False

        except SQLAlchemyError as e:
            log.error(f"Database error while deleting result: {e}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

    def clear_all_results(self) -> bool:
        """
        Clear all test results from the database.

        Returns:
            bool: True if successful, False otherwise.
        """
        session = None
        try:
            session = self.get_session()
            session.query(TestResultModel).delete()
            session.commit()
            log.info("All test results cleared from database")
            return True

        except SQLAlchemyError as e:
            log.error(f"Database error while clearing results: {e}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

    def close(self) -> None:
        """Close database connections."""
        try:
            self.engine.dispose()
            log.info("Database connections closed")
        except Exception as e:
            log.error(f"Error closing database connections: {e}")
