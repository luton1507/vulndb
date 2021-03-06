import json
import os
import tempfile

import pytest

import vulndb.lib.db as db
from vulndb.lib.gha import GitHubSource
from vulndb.lib.nvd import NvdSource
from vulndb.lib.utils import parse_cpe


@pytest.fixture
def test_db():
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        with tempfile.NamedTemporaryFile(delete=False) as indexfp:
            return db.get(db_file=fp.name, index_file=indexfp.name)


@pytest.fixture
def test_vuln_data():
    test_cve_data = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "data", "cve_data.json"
    )
    with open(test_cve_data, "r") as fp:
        json_data = json.loads(fp.read())
        nvdlatest = NvdSource()
        return nvdlatest.convert(json_data)


@pytest.fixture
def test_gha_data():
    test_cve_data = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "data", "gha_data.json"
    )
    with open(test_cve_data, "r") as fp:
        json_data = json.loads(fp.read())
        ghalatest = GitHubSource()
        return ghalatest.convert(json_data)[0]


def test_create(test_db, test_vuln_data):
    docs = db.store(test_db, test_vuln_data)
    assert len(docs) > len(test_vuln_data)


@pytest.mark.skip(reason="Slow test")
def test_search_slow(test_db, test_vuln_data):
    table = test_db
    docs = db.list_all(table)
    assert len(docs) == 0
    docs = db.store(test_db, test_vuln_data)
    assert len(docs) > 0
    all_data = db.list_all(table)
    assert all_data
    for d in all_data:
        res = db.pkg_search(
            table, d["details"]["package"], d["details"]["max_affected_version"]
        )
        assert len(res)
        assert res[0].to_dict()["package_issue"]


def test_search_fast(test_db, test_vuln_data):
    table = test_db
    docs = db.list_all(table)
    assert len(docs) == 0
    docs = db.store(test_db, test_vuln_data)
    assert len(docs) > 0
    all_data = db.list_all(table)
    assert all_data
    search_list = [
        d["details"]["package"] + "|" + d["details"]["max_affected_version"]
        for d in all_data
    ]
    res = db.pkg_bulk_search(test_db, search_list)
    assert len(res) > len(set(search_list))
    assert res[0].to_dict()["package_issue"]


def test_gha_create(test_db, test_gha_data):
    docs = db.store(test_db, test_gha_data)
    assert len(docs) > len(test_gha_data)


def test_gha_search_slow(test_db, test_gha_data):
    table = test_db
    docs = db.list_all(table)
    assert len(docs) == 0
    docs = db.store(test_db, test_gha_data)
    assert len(docs) > 0
    all_data = db.list_all(table)
    assert all_data
    for d in all_data:
        res = db.pkg_search(
            table, d["details"]["package"], d["details"]["max_affected_version"]
        )
        assert len(res)
        assert res[0].to_dict()["package_issue"]


def test_gha_vendor_search(test_db, test_gha_data):
    table = test_db
    docs = db.list_all(table)
    assert len(docs) == 0
    docs = db.store(test_db, test_gha_data)
    assert len(docs) > 0
    all_data = db.list_all(table)
    assert all_data
    for d in all_data:
        vendor, _, _ = parse_cpe(d["details"]["cpe_uri"])
        res = db.vendor_pkg_search(
            table, vendor, d["details"]["package"], d["details"]["max_affected_version"]
        )
        assert len(res)
        assert res[0].to_dict()["package_issue"]


def test_gha_search_bulk(test_db, test_gha_data):
    table = test_db
    docs = db.list_all(table)
    assert len(docs) == 0
    docs = db.store(test_db, test_gha_data)
    assert len(docs) > 0
    all_data = db.list_all(table)
    assert all_data
    tmp_list = [
        {
            "name": d["details"]["package"],
            "version": d["details"]["max_affected_version"],
        }
        for d in all_data
    ]
    res = db.bulk_index_search(tmp_list)
    assert len(res) > len(tmp_list)


def test_index_search(test_db, test_vuln_data):
    # This slow test ensures that every data in the main database is indexed
    table = test_db
    docs = db.list_all(table)
    assert len(docs) == 0
    docs = db.store(test_db, test_vuln_data)
    assert len(docs) > 0
    all_data = db.list_all(table)
    assert all_data
    tmp_list = []
    for d in all_data[:20]:
        tmp_list.append(
            {
                "name": d["details"]["package"],
                "version": d["details"]["max_affected_version"],
            }
        )
    res = db.bulk_index_search(tmp_list)
    assert len(res)
    for r in res:
        name_ver = r.split("|")
        fullres = db.index_search(name_ver[0], name_ver[1])
        assert fullres
