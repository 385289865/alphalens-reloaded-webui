"""Run alphalens analysis inline (without Celery) and store results in DuckDB."""
import sys, os, uuid, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.services.data_service import DataService
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.chart_service import ChartService
from backend.app.models.schemas import AnalysisConfig

SESSION_ID = '2daf93d2-0318-4c72-8271-f5dada52e62c'
DB_PATH = 'db/alphalens.db'

def main():
    # Wait for any lock to release
    time.sleep(2)

    ds = DataService(DB_PATH)
    task_id = str(uuid.uuid4())

    # Create analysis run via DataService methods
    config_dict = {
        "periods": [1, 5, 10], "quantiles": 5,
        "filter_zscore": 20, "max_loss": 0.35,
        "long_short": True, "group_neutral": False,
        "zero_aware": False, "cumulative_returns": True,
        "by_group": False, "bins": None, "groupby_column": None,
    }
    analysis_id = ds.create_analysis_run(SESSION_ID, task_id)

    analysis_service = AnalysisService(ds)
    chart_service = ChartService(ds)
    analysis_config = AnalysisConfig(**config_dict)

    def progress(stage, pct):
        ds.update_task_progress(task_id, analysis_id, 'running', stage, pct)
        print(f"  [{pct:3d}%] {stage}")

    try:
        ds.update_analysis_status(analysis_id, 'running')
        ds.link_task(analysis_id, task_id)

        print(f'Running analysis {analysis_id}...')
        analysis_service.run_full_analysis(analysis_id, SESSION_ID, analysis_config, progress)

        progress('generating_charts', 95)
        charts = chart_service.generate_all_charts(analysis_id)
        for ct, b64 in charts.items():
            if b64:
                ds.save_chart(analysis_id, ct, b64)

        ds.update_analysis_status(analysis_id, 'completed')
        ds.update_task_progress(task_id, analysis_id, 'completed', 'completed', 100,
                                'Analysis completed successfully')
        print(f'\n✅ Analysis {analysis_id} completed')
        print(f'Charts: {list(charts.keys())}')
    except Exception as e:
        print(f'\n❌ Analysis failed: {e}')
        import traceback
        traceback.print_exc()
        ds.update_analysis_status(analysis_id, 'failed', str(e))
        ds.update_task_progress(task_id, analysis_id, 'failed', 'error', 0, str(e))

    print(f'\nOpen: http://localhost:5173/sessions/{SESSION_ID}/analysis/{analysis_id}/results')

if __name__ == '__main__':
    main()
