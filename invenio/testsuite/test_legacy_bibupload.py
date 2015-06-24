# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import re
from tempfile import NamedTemporaryFile

from invenio.base.utils import run_py_func
from invenio.base.wrappers import lazy_import
from invenio.testsuite import InvenioXmlTestCase, make_test_suite, run_test_suite


CFG_TMPDIR = lazy_import('invenio.config.CFG_TMPDIR')
run_sql = lazy_import('invenio.legacy.dbquery.run_sql')
bibupload = lazy_import('invenio.legacy.bibupload.engine.main')


class BibUploadTests(InvenioXmlTestCase):

    @staticmethod
    def delete_record(recid):
        run_sql("""DELETE FROM bibrec WHERE id=%s""", (recid,))
        run_sql("""DELETE FROM bibfmt WHERE id_bibrec=%s""", (recid,))

    @staticmethod
    def create_xml_file(xml):
        xml_temp_file = NamedTemporaryFile(dir=CFG_TMPDIR)
        xml_temp_file.write(xml)
        xml_temp_file.flush()
        return xml_temp_file

    def test_upload_of_new_record_with_recid(self):
        """Test uploading a record to the database which already has an ID."""
        # Create temporary XML file
        recid = 96013
        xml_str = """<record>
              <controlfield tag="001">{recid}</controlfield>
              <datafield tag="100" ind1=" " ind2=" ">
                <subfield code="a">TEST_NAME2, TEST_NAME</subfield>
              </datafield>
        </record>""".format(recid=recid)
        xml_temp_file = self.create_xml_file(xml_str)

        self.delete_record(recid)
        self.assertFalse(run_sql("""SELECT id from bibrec WHERE id=%s""", (recid,)))
        try:
            # Run bibupload and see if it puts the right record in place
            out_pre = run_py_func(bibupload, ['bibupload', '-i', '-r', '--force',
                                          xml_temp_file.name]).out
            task_id = re.search('Task #([0-9]+) submitted', out_pre).groups()[0]
            out_post = run_py_func(bibupload, ['bibupload', task_id]).out
            recid_groups = re.search('Record ([0-9]+) DONE', out_post).groups()
            resulting_recid = recid_groups[0]
        finally:
            # Clean up after ourselves
            self.delete_record(resulting_recid)
        self.assertEqual(len(recid_groups), 1)
        self.assertIn('1 updated', out_post)  # returns 'updated' even if new,
                                              # but we've already checked that
                                              # it didn't previously exist anyway
        self.assertEqual(str(recid), resulting_recid)

    def test_upload_of_new_record_without_recid(self):
        """Test uploading a record to the database which does not have an ID."""
        # Create temporary XML file
        xml_str = """<record>
              <datafield tag="100" ind1=" " ind2=" ">
                <subfield code="a">TEST_NAME2, TEST_NAME</subfield>
              </datafield>
        </record>"""
        xml_temp_file = self.create_xml_file(xml_str)

        try:
            # Run bibupload and see if it puts the right record in place
            out_pre = run_py_func(bibupload, ['bibupload', '-i', '-r',
                                          xml_temp_file.name]).out
            task_id = re.search('Task #([0-9]+) submitted', out_pre).groups()[0]
            out_post = run_py_func(bibupload, ['bibupload', task_id]).out
            recid_groups = re.search('Record ([0-9]+) DONE', out_post).groups()
            recid = recid_groups[0]
        finally:
            # Clean up after ourselves
            self.delete_record(recid)
        self.assertIn('1 inserted', out_post)
        self.assertEqual(len(recid_groups), 1)



TEST_SUITE = make_test_suite(BibUploadTests)

if __name__ == '__main__':
    run_test_suite(TEST_SUITE)
